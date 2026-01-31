package com.predictionmarkets.scraper

import android.content.Intent
import android.os.Bundle
import android.text.Spannable
import android.text.SpannableStringBuilder
import android.text.style.ForegroundColorSpan
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.lifecycle.lifecycleScope
import com.predictionmarkets.scraper.databinding.ActivityMainBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private var scraper: PredictionMarketScraper? = null
    private var scrapeJob: Job? = null
    private var predictions: List<Prediction> = emptyList()
    private var lastSavedFile: File? = null

    private val logBuilder = SpannableStringBuilder()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupUI()
    }

    private fun setupUI() {
        binding.startButton.setOnClickListener {
            if (scrapeJob?.isActive == true) {
                stopScraping()
            } else {
                startScraping()
            }
        }

        binding.exportButton.setOnClickListener {
            exportToCsv()
        }

        binding.shareButton.setOnClickListener {
            shareCsv()
        }

        binding.clearLogButton.setOnClickListener {
            clearLog()
        }

        updateUI(isRunning = false)
    }

    private fun startScraping() {
        predictions = emptyList()
        lastSavedFile = null
        clearLog()

        scraper = PredictionMarketScraper { message ->
            lifecycleScope.launch(Dispatchers.Main) {
                appendLog(message)
            }
        }

        scrapeJob = lifecycleScope.launch {
            updateUI(isRunning = true)

            try {
                predictions = scraper?.scrapeAll() ?: emptyList()

                withContext(Dispatchers.Main) {
                    val kalshiCount = predictions.count { it.platform == "Kalshi" }
                    val polyCount = predictions.count { it.platform == "Polymarket" }

                    binding.kalshiCountText.text = "Kalshi: $kalshiCount"
                    binding.polymarketCountText.text = "Polymarket: $polyCount"
                    binding.totalCountText.text = "Total: ${predictions.size}"

                    if (predictions.isNotEmpty()) {
                        appendLog("\n" + "=".repeat(50))
                        appendLog("Preview (first 15):", LogLevel.INFO)
                        appendLog("-".repeat(70))

                        predictions.take(15).forEachIndexed { index, pred ->
                            val name = if (pred.name.length > 40) {
                                pred.name.take(37) + "..."
                            } else {
                                pred.name
                            }
                            appendLog("${index + 1}. [${pred.platform}] $name")
                            appendLog("   ${pred.formattedProbability()} | ${pred.formattedResolveDate()} | ${pred.verification.take(40)}")
                        }

                        appendLog("\nDone!", LogLevel.SUCCESS)
                        binding.statusText.text = "Found ${predictions.size} predictions"
                    } else {
                        appendLog("\nNo predictions matched the criteria.", LogLevel.ERROR)
                        binding.statusText.text = "No predictions found"
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    appendLog("Error: ${e.message}", LogLevel.ERROR)
                    binding.statusText.text = "Error occurred"
                }
            } finally {
                withContext(Dispatchers.Main) {
                    updateUI(isRunning = false)
                }
            }
        }
    }

    private fun stopScraping() {
        scraper?.cancel()
        scrapeJob?.cancel()
        appendLog("\nScraping cancelled by user", LogLevel.ERROR)
        binding.statusText.text = "Cancelled"
        updateUI(isRunning = false)
    }

    private fun updateUI(isRunning: Boolean) {
        binding.startButton.text = if (isRunning) {
            getString(R.string.stop_scraping)
        } else {
            getString(R.string.start_scraping)
        }

        binding.progressBar.visibility = if (isRunning) View.VISIBLE else View.GONE
        binding.exportButton.isEnabled = !isRunning && predictions.isNotEmpty()
        binding.shareButton.isEnabled = !isRunning && predictions.isNotEmpty()
    }

    private fun exportToCsv() {
        if (predictions.isEmpty()) {
            Toast.makeText(this, "No predictions to export", Toast.LENGTH_SHORT).show()
            return
        }

        lifecycleScope.launch {
            try {
                val file = withContext(Dispatchers.IO) {
                    savePredictionsToCsv(predictions)
                }

                lastSavedFile = file
                appendLog("\nSaved to: ${file.name}", LogLevel.SUCCESS)
                Toast.makeText(this@MainActivity, "Saved to ${file.name}", Toast.LENGTH_LONG).show()
            } catch (e: Exception) {
                appendLog("Export error: ${e.message}", LogLevel.ERROR)
                Toast.makeText(this@MainActivity, "Export failed: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun shareCsv() {
        if (predictions.isEmpty()) {
            Toast.makeText(this, "No predictions to share", Toast.LENGTH_SHORT).show()
            return
        }

        lifecycleScope.launch {
            try {
                val file = lastSavedFile ?: withContext(Dispatchers.IO) {
                    savePredictionsToCsv(predictions)
                }
                lastSavedFile = file

                val uri = FileProvider.getUriForFile(
                    this@MainActivity,
                    "${packageName}.fileprovider",
                    file
                )

                val shareIntent = Intent(Intent.ACTION_SEND).apply {
                    type = "text/csv"
                    putExtra(Intent.EXTRA_STREAM, uri)
                    putExtra(Intent.EXTRA_SUBJECT, "Prediction Markets Data")
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                }

                startActivity(Intent.createChooser(shareIntent, "Share CSV"))
            } catch (e: Exception) {
                appendLog("Share error: ${e.message}", LogLevel.ERROR)
                Toast.makeText(this@MainActivity, "Share failed: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun savePredictionsToCsv(predictions: List<Prediction>): File {
        val dateFormat = SimpleDateFormat("MM-dd", Locale.US)
        val dateStr = dateFormat.format(Date())

        var version = 1
        var filename: String
        var file: File

        do {
            filename = if (version == 1) {
                "prediction.markets.$dateStr.csv"
            } else {
                "prediction.markets.$dateStr.v$version.csv"
            }
            file = File(filesDir, filename)
            version++
        } while (file.exists())

        file.bufferedWriter().use { writer ->
            // Write header
            writer.write("Prediction Name,Yes Probability,Resolve Date,Platform,Verification")
            writer.newLine()

            // Write data
            for (pred in predictions) {
                val name = escapeCsvField(pred.name)
                val prob = pred.formattedProbability()
                val date = pred.formattedResolveDate()
                val platform = pred.platform
                val verification = escapeCsvField(pred.verification)

                writer.write("$name,$prob,$date,$platform,$verification")
                writer.newLine()
            }
        }

        return file
    }

    private fun escapeCsvField(field: String): String {
        return if (field.contains(",") || field.contains("\"") || field.contains("\n")) {
            "\"${field.replace("\"", "\"\"")}\""
        } else {
            field
        }
    }

    private enum class LogLevel {
        NORMAL, SUCCESS, ERROR, INFO
    }

    private fun appendLog(message: String, level: LogLevel = LogLevel.NORMAL) {
        val color = when (level) {
            LogLevel.SUCCESS -> ContextCompat.getColor(this, R.color.log_success)
            LogLevel.ERROR -> ContextCompat.getColor(this, R.color.log_error)
            LogLevel.INFO -> ContextCompat.getColor(this, R.color.log_info)
            LogLevel.NORMAL -> ContextCompat.getColor(this, R.color.log_text)
        }

        val start = logBuilder.length
        logBuilder.append(message)
        logBuilder.append("\n")
        logBuilder.setSpan(
            ForegroundColorSpan(color),
            start,
            logBuilder.length,
            Spannable.SPAN_EXCLUSIVE_EXCLUSIVE
        )

        binding.logText.text = logBuilder

        // Auto-scroll to bottom
        binding.logScrollView.post {
            binding.logScrollView.fullScroll(View.FOCUS_DOWN)
        }
    }

    private fun clearLog() {
        logBuilder.clear()
        binding.logText.text = ""
        binding.kalshiCountText.text = "Kalshi: 0"
        binding.polymarketCountText.text = "Polymarket: 0"
        binding.totalCountText.text = "Total: 0"
        binding.statusText.text = "Ready to scrape"
    }

    override fun onDestroy() {
        super.onDestroy()
        scraper?.cancel()
        scrapeJob?.cancel()
    }
}
