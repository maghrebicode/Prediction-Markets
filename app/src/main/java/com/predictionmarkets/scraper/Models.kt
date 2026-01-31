package com.predictionmarkets.scraper

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

/**
 * Internal prediction model used for combining results from all platforms.
 */
data class Prediction(
    val name: String,
    val probability: Double,
    val resolveDate: ZonedDateTime?,
    val platform: String,
    val verification: String,
    val openInterest: Long = 0
) {
    fun formattedProbability(): String = "${probability.toInt()}%"

    fun formattedResolveDate(): String = resolveDate?.let {
        it.format(DateTimeFormatter.ofPattern("yyyy-MM-dd"))
    } ?: "Unknown"
}

// ============================================================
// KALSHI API MODELS
// ============================================================

@Serializable
data class KalshiMarketsResponse(
    val markets: List<KalshiMarket> = emptyList(),
    val cursor: String? = null
)

@Serializable
data class KalshiMarket(
    val ticker: String = "",
    @SerialName("event_ticker")
    val eventTicker: String = "",
    val title: String = "",
    val subtitle: String = "",
    val status: String = "",
    @SerialName("yes_bid")
    val yesBid: Double? = null,
    @SerialName("yes_ask")
    val yesAsk: Double? = null,
    @SerialName("last_price")
    val lastPrice: Double? = null,
    @SerialName("open_interest")
    val openInterest: Long? = null,
    @SerialName("expected_expiration_time")
    val expectedExpirationTime: String? = null,
    @SerialName("expiration_time")
    val expirationTime: String? = null,
    @SerialName("close_time")
    val closeTime: String? = null,
    @SerialName("rules_primary")
    val rulesPrimary: String? = null,
    @SerialName("rules_secondary")
    val rulesSecondary: String? = null
)

// ============================================================
// POLYMARKET API MODELS
// ============================================================

@Serializable
data class PolymarketEvent(
    val id: String = "",
    val title: String = "",
    val slug: String = "",
    val description: String? = null,
    val endDate: String? = null,
    val resolutionSource: String? = null,
    val tags: List<PolymarketTag> = emptyList(),
    val markets: List<PolymarketMarket> = emptyList()
)

@Serializable
data class PolymarketTag(
    val id: String = "",
    val label: String? = null,
    val slug: String? = null
)

@Serializable
data class PolymarketMarket(
    val id: String = "",
    val question: String = "",
    val description: String? = null,
    val endDate: String? = null,
    val resolutionSource: String? = null,
    val outcomePrices: String? = null,  // JSON string like "[0.45, 0.55]"
    val outcomes: String? = null  // JSON string like "[\"Yes\", \"No\"]"
)
