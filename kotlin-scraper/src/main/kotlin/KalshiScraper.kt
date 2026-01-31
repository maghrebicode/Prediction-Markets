package kalshi

import java.net.HttpURLConnection
import java.net.URL
import org.json.JSONObject
import org.json.JSONArray

data class Market(
    val ticker: String,
    val title: String,
    val subtitle: String,
    val eventTicker: String,
    val openInterest: Int,
    val volume: Int,
    val yesBid: Double,
    val yesAsk: Double,
    val lastPrice: Double,
    val closeTime: String
)

class KalshiScraper {

    companion object {
        private const val BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

        private val SPORTS_KEYWORDS = listOf(
            "nfl", "nba", "mlb", "nhl", "ncaa", "football", "basketball",
            "baseball", "hockey", "soccer", "tennis", "golf", "ufc", "mma",
            "boxing", "wrestling", "racing", "f1", "nascar", "pga", "fifa",
            "world cup", "super bowl", "playoffs", "championship", "league",
            "team", "player", "game", "match", "score", "win", "loss",
            "patriots", "eagles", "chiefs", "49ers", "cowboys", "packers",
            "lakers", "celtics", "warriors", "bulls", "heat", "nets",
            "yankees", "dodgers", "cubs", "red sox", "mets", "braves",
            "athlete", "coach", "mvp", "touchdown", "homerun", "slam dunk"
        )
    }

    private fun isSportsMarket(market: JSONObject): Boolean {
        val text = listOf(
            market.optString("title", ""),
            market.optString("subtitle", ""),
            market.optString("event_ticker", ""),
            market.optString("ticker", "")
        ).joinToString(" ").lowercase()

        return SPORTS_KEYWORDS.any { it in text }
    }

    fun calcProbability(market: Market): Double? {
        val bid = market.yesBid
        val ask = market.yesAsk
        val last = market.lastPrice

        return when {
            bid > 0 && ask > 0 -> ((bid + ask) / 2).roundTo(1)
            last > 0 -> last.roundTo(1)
            ask > 0 -> ask.roundTo(1)
            bid > 0 -> bid.roundTo(1)
            else -> null
        }
    }

    private fun Double.roundTo(decimals: Int): Double {
        var multiplier = 1.0
        repeat(decimals) { multiplier *= 10 }
        return kotlin.math.round(this * multiplier) / multiplier
    }

    private fun parseMarket(json: JSONObject): Market {
        return Market(
            ticker = json.optString("ticker", ""),
            title = json.optString("title", ""),
            subtitle = json.optString("subtitle", ""),
            eventTicker = json.optString("event_ticker", ""),
            openInterest = json.optInt("open_interest", 0),
            volume = json.optInt("volume", 0),
            yesBid = json.optDouble("yes_bid", 0.0),
            yesAsk = json.optDouble("yes_ask", 0.0),
            lastPrice = json.optDouble("last_price", 0.0),
            closeTime = json.optString("close_time", "")
        )
    }

    fun fetchMarkets(onProgress: (String) -> Unit = {}): List<Market> {
        val allMarkets = mutableListOf<Market>()
        var cursor: String? = null
        var page = 0

        onProgress("Fetching markets from Kalshi...")

        while (true) {
            page++
            try {
                val urlStr = buildString {
                    append("$BASE_URL/markets?limit=200&status=open")
                    cursor?.let { append("&cursor=$it") }
                }

                val url = URL(urlStr)
                val connection = url.openConnection() as HttpURLConnection
                connection.requestMethod = "GET"
                connection.connectTimeout = 30000
                connection.readTimeout = 30000

                if (connection.responseCode != 200) {
                    onProgress("Error on page $page: HTTP ${connection.responseCode}")
                    break
                }

                val response = connection.inputStream.bufferedReader().readText()
                val data = JSONObject(response)

                val markets = data.optJSONArray("markets") ?: JSONArray()
                if (markets.length() == 0) break

                for (i in 0 until markets.length()) {
                    val marketJson = markets.getJSONObject(i)
                    if (!isSportsMarket(marketJson)) {
                        allMarkets.add(parseMarket(marketJson))
                    }
                }

                onProgress("Page $page: ${markets.length()} fetched, ${allMarkets.size} non-sports total")

                cursor = data.optString("cursor", null)
                if (cursor.isNullOrEmpty()) break

                Thread.sleep(300)

            } catch (e: Exception) {
                onProgress("Error on page $page: ${e.message}")
                break
            }
        }

        // Sort by open interest + volume, take top 100
        return allMarkets
            .sortedByDescending { it.openInterest + it.volume }
            .take(100)
    }
}
