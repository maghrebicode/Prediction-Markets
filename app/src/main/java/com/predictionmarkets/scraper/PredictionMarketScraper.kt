package com.predictionmarkets.scraper

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.double
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit
import java.util.concurrent.TimeUnit

/**
 * Prediction Market Data Scraper
 * Kotlin/Android port of the Python scraper
 * Fetches Economics and Politics predictions from Kalshi.com and Polymarket.com
 */
class PredictionMarketScraper(
    private val logCallback: (String) -> Unit = {}
) {
    companion object {
        // Configuration
        const val MIN_YES_PROBABILITY = 10.0  // Minimum 10% threshold
        const val MAX_YES_PROBABILITY = 90.0  // Maximum 90% threshold
        const val MIN_DAYS_TO_RESOLVE = 1L    // Exclude markets resolving within 1 day

        // Kalshi API
        const val KALSHI_API_URL = "https://api.elections.kalshi.com/trade-api/v2/markets"

        // Polymarket API
        const val POLYMARKET_API_URL = "https://gamma-api.polymarket.com/events"

        // Kalshi patterns for Economics category
        val KALSHI_ECONOMICS_PATTERNS = listOf(
            "infl", "cpi", "fed", "fomc", "gdp", "recession", "unemployment",
            "jobs", "nonfarm", "payroll", "treasury", "yield", "rate", "debt",
            "deficit", "trade", "tariff", "stock", "sp500", "nasdaq", "dow",
            "bitcoin", "btc", "eth", "crypto", "oil", "gas", "gold", "commodity",
            "housing", "mortgage", "economy", "econ", "financial", "ipo"
        )

        // Kalshi patterns for Politics category
        val KALSHI_POLITICS_PATTERNS = listOf(
            "pres", "potus", "trump", "biden", "elect", "vote", "congress",
            "senate", "house", "governor", "mayor", "scotus", "supreme",
            "cabinet", "secretary", "confirm", "impeach", "indictment",
            "primary", "caucus", "poll", "approval", "democrat",
            "republican", "gop", "political", "politic", "gov",
            "legislation", "bill", "executive", "veto", "pardon",
            "musk", "doge", "rfk", "vance", "harris"
        )

        // Patterns to exclude (sports, weather, entertainment)
        val KALSHI_EXCLUDE_PATTERNS = listOf(
            "kxnba", "kxnfl", "kxmlb", "kxnhl", "kxncaa", "kxpga", "kxufc",
            "kxsoccer", "kxtennis", "kxgolf", "kxboxing", "kxracing",
            "kxnascar", "kxf1", "kxmma", "kxsport",
            "nba", "nfl", "mlb", "nhl", "ncaa", "pga", "ufc",
            "soccer", "football", "basketball", "baseball", "hockey",
            "tennis", "golf", "boxing", "racing", "nascar", "mma",
            "weather", "temperature", "rain", "snow", "hurricane", "tornado",
            "oscar", "emmy", "grammy", "movie", "film", "streamer",
            "youtube", "tiktok", "influencer", "subscriber"
        )

        // Polymarket tag IDs for categories we want
        val POLYMARKET_INCLUDE_TAGS = listOf(2, 120, 21, 100265)  // Politics, Finance, Crypto, Geopolitics

        // Polymarket tag IDs to exclude
        val POLYMARKET_EXCLUDE_TAGS = listOf(100639)  // Sports

        val POLYMARKET_EXCLUDE_PATTERNS = listOf(
            "nba", "nfl", "mlb", "nhl", "ncaa", "pga", "ufc",
            "soccer", "football", "basketball", "baseball", "hockey",
            "tennis", "golf", "boxing", "racing", "nascar", "mma",
            "oscar", "emmy", "grammy", "movie", "film",
            "youtube", "tiktok", "influencer", "streamer"
        )

        // Source patterns for verification extraction
        val SOURCE_PATTERNS = listOf(
            "Bureau of Labor Statistics" to listOf("bls.gov", "bureau of labor statistics", "bls "),
            "Federal Reserve" to listOf("federal reserve", "federalreserve.gov", "fed.gov", "fomc"),
            "Bureau of Economic Analysis" to listOf("bea.gov", "bureau of economic analysis"),
            "Treasury Department" to listOf("treasury.gov", "treasury department"),
            "Census Bureau" to listOf("census.gov", "census bureau"),
            "SEC" to listOf("sec.gov", "securities and exchange"),
            "Congress.gov" to listOf("congress.gov"),
            "White House" to listOf("whitehouse.gov", "white house"),
            "Associated Press" to listOf("associated press", "ap news", "apnews"),
            "Reuters" to listOf("reuters"),
            "Bloomberg" to listOf("bloomberg"),
            "CoinGecko" to listOf("coingecko"),
            "CoinMarketCap" to listOf("coinmarketcap"),
            "Official Government Source" to listOf("official", "government")
        )
    }

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        coerceInputValues = true
    }

    @Volatile
    private var isCancelled = false

    fun cancel() {
        isCancelled = true
    }

    private fun log(message: String) {
        logCallback(message)
    }

    // ============================================================
    // UTILITY FUNCTIONS
    // ============================================================

    private fun cleanVerificationText(text: String?): String {
        if (text.isNullOrBlank()) return ""
        // Remove HTML tags
        var cleaned = text.replace(Regex("<[^>]+>"), "")
        // Remove extra whitespace
        cleaned = cleaned.split(Regex("\\s+")).joinToString(" ")
        // Truncate if too long
        if (cleaned.length > 200) {
            cleaned = cleaned.take(197) + "..."
        }
        return cleaned.trim()
    }

    private fun extractSourcesFromText(text: String?): List<String> {
        if (text.isNullOrBlank()) return emptyList()

        val sources = mutableListOf<String>()
        val textLower = text.lowercase()

        for ((sourceName, patterns) in SOURCE_PATTERNS) {
            for (pattern in patterns) {
                if (pattern in textLower) {
                    if (sourceName !in sources) {
                        sources.add(sourceName)
                    }
                    break
                }
            }
        }

        return sources
    }

    private fun parseIsoDateTime(dateStr: String?): ZonedDateTime? {
        if (dateStr.isNullOrBlank()) return null
        return try {
            val normalized = dateStr.replace("Z", "+00:00")
            ZonedDateTime.parse(normalized, DateTimeFormatter.ISO_OFFSET_DATE_TIME)
        } catch (e: Exception) {
            try {
                ZonedDateTime.parse(dateStr)
            } catch (e2: Exception) {
                null
            }
        }
    }

    // ============================================================
    // KALSHI FUNCTIONS
    // ============================================================

    private suspend fun fetchKalshiMarkets(cursor: String? = null): KalshiMarketsResponse {
        return withContext(Dispatchers.IO) {
            val urlBuilder = KALSHI_API_URL.toHttpUrl().newBuilder()
                .addQueryParameter("limit", "200")
                .addQueryParameter("status", "open")
                .addQueryParameter("mve_filter", "exclude")

            cursor?.let { urlBuilder.addQueryParameter("cursor", it) }

            val request = Request.Builder()
                .url(urlBuilder.build())
                .header("Accept", "application/json")
                .header("User-Agent", "Mozilla/5.0 (Android; Mobile)")
                .get()
                .build()

            val response = httpClient.newCall(request).execute()
            val body = response.body?.string() ?: throw Exception("Empty response body")

            if (!response.isSuccessful) {
                throw Exception("HTTP ${response.code}: ${response.message}")
            }

            json.decodeFromString<KalshiMarketsResponse>(body)
        }
    }

    private fun kalshiShouldExclude(market: KalshiMarket): Boolean {
        val combined = "${market.ticker} ${market.eventTicker} ${market.title}".lowercase()
        return KALSHI_EXCLUDE_PATTERNS.any { it in combined }
    }

    private fun kalshiIsEconomicsOrPolitics(market: KalshiMarket): Boolean {
        val combined = "${market.ticker} ${market.eventTicker} ${market.title} ${market.subtitle}".lowercase()

        if (KALSHI_ECONOMICS_PATTERNS.any { it in combined }) return true
        if (KALSHI_POLITICS_PATTERNS.any { it in combined }) return true

        return false
    }

    private fun kalshiGetProbability(market: KalshiMarket): Double {
        return market.yesBid ?: market.yesAsk ?: market.lastPrice ?: 0.0
    }

    private fun kalshiGetResolveDate(market: KalshiMarket): ZonedDateTime? {
        val dateStr = market.expectedExpirationTime
            ?: market.expirationTime
            ?: market.closeTime
        return parseIsoDateTime(dateStr)
    }

    private fun kalshiGetVerification(market: KalshiMarket): String {
        val sources = mutableListOf<String>()

        // Check rules fields
        val allRules = "${market.rulesPrimary ?: ""} ${market.rulesSecondary ?: ""}"
        sources.addAll(extractSourcesFromText(allRules))

        // Check event ticker for clues about data source
        val eventTicker = market.eventTicker.uppercase()

        when {
            "CPI" in eventTicker || "INFL" in eventTicker -> {
                if ("Bureau of Labor Statistics" !in sources) sources.add("Bureau of Labor Statistics")
            }
            "GDP" in eventTicker -> {
                if ("Bureau of Economic Analysis" !in sources) sources.add("Bureau of Economic Analysis")
            }
            "FED" in eventTicker || "FOMC" in eventTicker -> {
                if ("Federal Reserve" !in sources) sources.add("Federal Reserve")
            }
            "JOBS" in eventTicker || "NONFARM" in eventTicker || "UNEMPLOYMENT" in eventTicker -> {
                if ("Bureau of Labor Statistics" !in sources) sources.add("Bureau of Labor Statistics")
            }
        }

        // Default if no sources found
        if (sources.isEmpty()) {
            sources.add("Kalshi Resolution")
        }

        return sources.joinToString("; ")
    }

    suspend fun scrapeKalshi(minResolveDate: ZonedDateTime): List<Prediction> {
        log("\n${"=".repeat(50)}")
        log("KALSHI SCRAPING")
        log("=".repeat(50))

        val allMarkets = mutableListOf<KalshiMarket>()
        var cursor: String? = null
        var page = 1

        while (!isCancelled) {
            log("Kalshi page $page...")

            try {
                val data = fetchKalshiMarkets(cursor)
                val markets = data.markets

                if (markets.isEmpty()) break

                allMarkets.addAll(markets)
                cursor = data.cursor

                if (cursor.isNullOrBlank()) break

                page++
                delay(300)

                if (page > 50) {
                    log("WARNING: Kalshi page limit reached")
                    break
                }
            } catch (e: Exception) {
                log("ERROR Kalshi: ${e.message}")
                break
            }
        }

        log("Kalshi raw markets: ${allMarkets.size}")

        // Filter markets
        val filtered = allMarkets.mapNotNull { market ->
            if (kalshiShouldExclude(market)) return@mapNotNull null
            if (!kalshiIsEconomicsOrPolitics(market)) return@mapNotNull null

            val prob = kalshiGetProbability(market)
            if (prob < MIN_YES_PROBABILITY || prob > MAX_YES_PROBABILITY) return@mapNotNull null

            val resolveDate = kalshiGetResolveDate(market)
            if (resolveDate != null && resolveDate.isBefore(minResolveDate)) return@mapNotNull null

            val title = market.title.trim()
            val subtitle = market.subtitle.trim()
            val name = if (subtitle.isNotBlank() && subtitle != title) {
                "$title - $subtitle"
            } else {
                title
            }

            Prediction(
                name = name,
                probability = prob,
                resolveDate = resolveDate,
                platform = "Kalshi",
                verification = kalshiGetVerification(market),
                openInterest = market.openInterest ?: 0
            )
        }

        log("Kalshi filtered: ${filtered.size}")
        return filtered
    }

    // ============================================================
    // POLYMARKET FUNCTIONS
    // ============================================================

    private suspend fun fetchPolymarketEvents(offset: Int = 0, tagId: Int? = null): List<PolymarketEvent> {
        return withContext(Dispatchers.IO) {
            val urlBuilder = POLYMARKET_API_URL.toHttpUrl().newBuilder()
                .addQueryParameter("limit", "100")
                .addQueryParameter("offset", offset.toString())
                .addQueryParameter("active", "true")
                .addQueryParameter("closed", "false")
                .addQueryParameter("order", "volume24hr")
                .addQueryParameter("ascending", "false")

            tagId?.let { urlBuilder.addQueryParameter("tag_id", it.toString()) }

            val request = Request.Builder()
                .url(urlBuilder.build())
                .header("Accept", "application/json")
                .header("User-Agent", "Mozilla/5.0 (Android; Mobile)")
                .get()
                .build()

            val response = httpClient.newCall(request).execute()
            val body = response.body?.string() ?: throw Exception("Empty response body")

            if (!response.isSuccessful) {
                throw Exception("HTTP ${response.code}: ${response.message}")
            }

            json.decodeFromString<List<PolymarketEvent>>(body)
        }
    }

    private fun polymarketShouldExclude(event: PolymarketEvent, market: PolymarketMarket): Boolean {
        val combined = "${event.title} ${market.question} ${event.slug}".lowercase()

        if (POLYMARKET_EXCLUDE_PATTERNS.any { it in combined }) return true

        // Check tags
        for (tag in event.tags) {
            val tagId = tag.id.toIntOrNull()
            if (tagId != null && tagId in POLYMARKET_EXCLUDE_TAGS) return true
        }

        return false
    }

    private fun polymarketGetProbability(market: PolymarketMarket): Double {
        return try {
            val pricesStr = market.outcomePrices ?: return 0.0
            val prices = json.decodeFromString<JsonArray>(pricesStr)
            if (prices.isNotEmpty()) {
                prices[0].jsonPrimitive.double * 100
            } else {
                0.0
            }
        } catch (e: Exception) {
            0.0
        }
    }

    private fun polymarketGetResolveDate(event: PolymarketEvent, market: PolymarketMarket): ZonedDateTime? {
        val dateStr = market.endDate ?: event.endDate
        return parseIsoDateTime(dateStr)
    }

    private fun polymarketGetVerification(event: PolymarketEvent, market: PolymarketMarket): String {
        val sources = mutableListOf<String>()

        // Check resolution source field
        val resolutionSource = market.resolutionSource ?: event.resolutionSource
        if (!resolutionSource.isNullOrBlank()) {
            sources.add(cleanVerificationText(resolutionSource))
        }

        // Check description for sources
        val description = market.description ?: event.description
        val extracted = extractSourcesFromText(description)
        for (src in extracted) {
            if (src !in sources) sources.add(src)
        }

        // Polymarket uses UMA Oracle for all resolutions
        if ("UMA Oracle" !in sources) {
            sources.add("UMA Oracle")
        }

        return if (sources.isNotEmpty()) sources.joinToString("; ") else "UMA Oracle"
    }

    suspend fun scrapePolymarket(minResolveDate: ZonedDateTime): List<Prediction> {
        log("\n${"=".repeat(50)}")
        log("POLYMARKET SCRAPING")
        log("=".repeat(50))

        val allMarkets = mutableListOf<Prediction>()
        val seenIds = mutableSetOf<String>()

        val tagNames = mapOf(
            2 to "Politics",
            120 to "Finance",
            21 to "Crypto",
            100265 to "Geopolitics"
        )

        // Fetch by each relevant tag
        for (tagId in POLYMARKET_INCLUDE_TAGS) {
            if (isCancelled) break

            log("\nFetching ${tagNames[tagId] ?: tagId}...")

            var offset = 0
            var tagTotal = 0

            while (!isCancelled) {
                try {
                    val events = fetchPolymarketEvents(offset = offset, tagId = tagId)

                    if (events.isEmpty()) break

                    for (event in events) {
                        for (market in event.markets) {
                            val marketId = market.id
                            if (marketId in seenIds) continue
                            seenIds.add(marketId)

                            if (polymarketShouldExclude(event, market)) continue

                            val prob = polymarketGetProbability(market)
                            if (prob < MIN_YES_PROBABILITY || prob > MAX_YES_PROBABILITY) continue

                            val resolveDate = polymarketGetResolveDate(event, market)
                            if (resolveDate != null && resolveDate.isBefore(minResolveDate)) continue

                            // Build name from event title and market question
                            val eventTitle = event.title.trim()
                            val question = market.question.trim()

                            val name = if (question.isNotBlank() && question != eventTitle) {
                                "$eventTitle: $question"
                            } else {
                                eventTitle.ifBlank { question }
                            }

                            allMarkets.add(
                                Prediction(
                                    name = name,
                                    probability = prob,
                                    resolveDate = resolveDate,
                                    platform = "Polymarket",
                                    verification = polymarketGetVerification(event, market),
                                    openInterest = 0
                                )
                            )
                            tagTotal++
                        }
                    }

                    offset += 100
                    delay(300)

                    if (events.size < 100) break
                    if (offset > 1000) break

                } catch (e: Exception) {
                    log("   ERROR: ${e.message}")
                    break
                }
            }

            log("   Found $tagTotal markets")
        }

        log("\nPolymarket total: ${allMarkets.size}")
        return allMarkets
    }

    // ============================================================
    // MAIN SCRAPE FUNCTION
    // ============================================================

    suspend fun scrapeAll(): List<Prediction> {
        isCancelled = false

        log("Prediction Market Scraper")
        log("=".repeat(50))
        log("Platforms: Kalshi + Polymarket")
        log("Filters: ${MIN_YES_PROBABILITY.toInt()}%-${MAX_YES_PROBABILITY.toInt()}%, resolve > $MIN_DAYS_TO_RESOLVE day(s)")
        log("Categories: Economics & Politics only")

        val now = ZonedDateTime.now()
        val minResolveDate = now.plus(MIN_DAYS_TO_RESOLVE, ChronoUnit.DAYS)

        val allPredictions = mutableListOf<Prediction>()

        // Scrape Kalshi
        if (!isCancelled) {
            try {
                val kalshiMarkets = scrapeKalshi(minResolveDate)
                allPredictions.addAll(kalshiMarkets)
            } catch (e: Exception) {
                log("ERROR Kalshi scraping failed: ${e.message}")
            }
        }

        // Scrape Polymarket
        if (!isCancelled) {
            try {
                val polyMarkets = scrapePolymarket(minResolveDate)
                allPredictions.addAll(polyMarkets)
            } catch (e: Exception) {
                log("ERROR Polymarket scraping failed: ${e.message}")
            }
        }

        log("\n${"=".repeat(50)}")
        log("RESULTS SUMMARY")
        log("=".repeat(50))

        val kalshiCount = allPredictions.count { it.platform == "Kalshi" }
        val polyCount = allPredictions.count { it.platform == "Polymarket" }

        log("Kalshi predictions: $kalshiCount")
        log("Polymarket predictions: $polyCount")
        log("Total predictions: ${allPredictions.size}")

        // Sort by open interest then alphabetically
        return allPredictions.sortedWith(
            compareByDescending<Prediction> { it.openInterest }
                .thenBy { it.name }
        )
    }
}
