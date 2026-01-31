# Prediction Markets Scraper

Android application that fetches Economics and Politics prediction market data from Kalshi.com and Polymarket.com.

## Features

- Scrapes prediction markets from Kalshi and Polymarket APIs
- Filters for Economics and Politics categories
- Excludes sports, weather, and entertainment markets
- Filters by probability range (10%-90% Yes probability)
- Excludes markets resolving within 1 day
- Exports results to CSV
- Share CSV via Android share sheet

## Requirements

- Android Studio Hedgehog (2023.1.1) or newer
- Android SDK 34
- Kotlin 1.9.20+
- JDK 17

## Building

1. Open the project in Android Studio
2. Sync Gradle files
3. Build and run on device/emulator

```bash
# Or build from command line
./gradlew assembleDebug
```

## Project Structure

```
app/src/main/java/com/predictionmarkets/scraper/
├── MainActivity.kt           # Main UI activity
├── Models.kt                 # Data models for API responses
└── PredictionMarketScraper.kt # Core scraping logic
```

## Configuration

Edit `PredictionMarketScraper.kt` to adjust:

- `MIN_YES_PROBABILITY` - Minimum probability threshold (default: 10%)
- `MAX_YES_PROBABILITY` - Maximum probability threshold (default: 90%)
- `MIN_DAYS_TO_RESOLVE` - Minimum days until resolution (default: 1)
- Pattern lists for filtering categories

## APIs Used

- **Kalshi**: `https://api.elections.kalshi.com/trade-api/v2/markets`
- **Polymarket**: `https://gamma-api.polymarket.com/events`

## Original Python Version

The original Python scraper (`kalshi_scraper.py`) is also included for reference, optimized for Pydroid 3 on Android.
