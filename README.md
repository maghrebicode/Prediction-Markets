# Prediction Markets Scraper for Android

Android application that fetches Economics and Politics prediction market data from Kalshi.com and Polymarket.com.

## Features

- Scrapes prediction markets from Kalshi and Polymarket APIs
- Filters for Economics and Politics categories
- Excludes sports, weather, and entertainment markets
- Filters by probability range (10%-90% Yes probability)
- Excludes markets resolving within 1 day
- Exports results to CSV
- Share CSV via Android share sheet

---

## JStudio Setup (Step-by-Step)

### Step 1: Install JStudio

1. Open **Google Play Store** on your Android device
2. Search for **"JStudio - IDE for Java"** or **"Java N-IDE"**
3. Install the app
4. Open JStudio and grant storage permissions when prompted

### Step 2: Create New Project

1. Open JStudio
2. Tap **"New Project"** or the **+** button
3. Select **"Android App (Kotlin)"** template
4. Enter project details:
   - **Project Name**: `PredictionMarketsScraper`
   - **Package Name**: `com.predictionmarkets.scraper`
   - **Save Location**: Choose your preferred folder
5. Tap **Create**

### Step 3: Replace Project Files

After creating the project, you need to replace the auto-generated files with the ones from this repository.

#### 3a. Replace `build.gradle` (Project Level)
Navigate to the root project folder and replace `build.gradle` with:

```groovy
plugins {
    id 'com.android.application' version '8.2.0' apply false
    id 'org.jetbrains.kotlin.android' version '1.9.20' apply false
    id 'org.jetbrains.kotlin.plugin.serialization' version '1.9.20' apply false
}
```

#### 3b. Replace `app/build.gradle` (App Level)
Open `app/build.gradle` and replace entirely with the content from `app/build.gradle` in this repo.

#### 3c. Replace `settings.gradle`
Replace with the content from `settings.gradle` in this repo.

### Step 4: Copy Source Files

Copy these Kotlin files to `app/src/main/java/com/predictionmarkets/scraper/`:

1. **MainActivity.kt** - Main UI activity
2. **Models.kt** - Data models for API responses
3. **PredictionMarketScraper.kt** - Core scraping logic

### Step 5: Copy Resource Files

Copy these to `app/src/main/res/`:

1. **layout/activity_main.xml** - Main screen layout
2. **values/strings.xml** - String resources
3. **values/colors.xml** - Color definitions
4. **values/themes.xml** - App theme
5. **xml/file_paths.xml** - FileProvider paths
6. **drawable/ic_launcher_foreground.xml** - App icon foreground
7. **drawable/ic_launcher_background.xml** - App icon background
8. **mipmap-anydpi-v26/ic_launcher.xml** - Adaptive icon
9. **mipmap-anydpi-v26/ic_launcher_round.xml** - Round adaptive icon

### Step 6: Update AndroidManifest.xml

Replace `app/src/main/AndroidManifest.xml` with the content from this repo.

### Step 7: Sync and Build

1. In JStudio, tap the **Sync** button (or Menu > Sync Project)
2. Wait for Gradle to download dependencies
3. Tap **Build** > **Build APK**
4. Wait for the build to complete

### Step 8: Install and Run

1. Once built, tap **Run** or find the APK in the build output folder
2. Install the APK on your device
3. Open the app and tap **"Start Scraping"**

---

## Alternative: Manual File Copy Method

If you have a file manager:

1. Download/clone this repository to your device
2. Use a file manager to navigate to the downloaded folder
3. Copy all files maintaining the folder structure to your JStudio project folder
4. Open JStudio and sync the project

---

## Using the App

1. **Start Scraping**: Tap to begin fetching markets from Kalshi and Polymarket
2. **Stop**: Tap to cancel the current scraping operation
3. **Export CSV**: Save results to a CSV file on your device
4. **Share CSV**: Share the CSV file via email, messaging apps, etc.

The log output shows real-time progress as markets are fetched and filtered.

---

## Project Structure

```
app/src/main/
├── AndroidManifest.xml
├── java/com/predictionmarkets/scraper/
│   ├── MainActivity.kt           # Main UI activity
│   ├── Models.kt                 # Data models for API responses
│   └── PredictionMarketScraper.kt # Core scraping logic
└── res/
    ├── layout/activity_main.xml  # UI layout
    ├── values/                   # Colors, strings, themes
    ├── drawable/                 # Vector icons
    ├── mipmap-anydpi-v26/        # Adaptive icons
    └── xml/file_paths.xml        # FileProvider config
```

---

## Configuration

Edit `PredictionMarketScraper.kt` to adjust filtering:

- `MIN_YES_PROBABILITY` - Minimum probability (default: 10%)
- `MAX_YES_PROBABILITY` - Maximum probability (default: 90%)
- `MIN_DAYS_TO_RESOLVE` - Minimum days until resolution (default: 1)
- Pattern lists for category filtering

---

## Troubleshooting

### "Could not resolve dependencies"
- Make sure you have internet connection
- Tap Sync again
- Check that JStudio has latest SDK tools

### "Unresolved reference" errors
- Ensure all Kotlin files are in the correct package folder
- Check package declaration at top of each file matches `com.predictionmarkets.scraper`

### Build fails with Java version error
- In JStudio settings, ensure JDK 17 is selected
- Or change `compileOptions` in `app/build.gradle` to use Java 11

### Network errors when scraping
- Ensure device has internet connection
- Check that app has internet permission granted

---

## APIs Used

- **Kalshi**: `https://api.elections.kalshi.com/trade-api/v2/markets`
- **Polymarket**: `https://gamma-api.polymarket.com/events`

---

## Original Python Version

The original Python scraper (`kalshi_scraper.py`) is also included, optimized for Pydroid 3.
