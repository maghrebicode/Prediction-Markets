package kalshi

import java.awt.*
import java.io.File
import java.io.FileWriter
import javax.swing.*
import javax.swing.table.DefaultTableModel

class MainUI : JFrame("Kalshi Top 100 Non-Sports Markets") {

    private val scraper = KalshiScraper()
    private val tableModel = DefaultTableModel()
    private val table = JTable(tableModel)
    private val statusLabel = JLabel("Ready")
    private val progressArea = JTextArea(6, 50)
    private val fetchButton = JButton("Fetch Markets")
    private val exportButton = JButton("Export to CSV")

    private var markets: List<Market> = emptyList()

    init {
        setupUI()
        setupActions()
    }

    private fun setupUI() {
        defaultCloseOperation = EXIT_ON_CLOSE
        size = Dimension(1000, 700)
        layout = BorderLayout(10, 10)

        // Header panel
        val headerPanel = JPanel(BorderLayout()).apply {
            border = BorderFactory.createEmptyBorder(10, 10, 5, 10)
            val titleLabel = JLabel("Kalshi Top 100 Non-Sports Markets").apply {
                font = Font("SansSerif", Font.BOLD, 18)
            }
            add(titleLabel, BorderLayout.WEST)

            val buttonPanel = JPanel(FlowLayout(FlowLayout.RIGHT)).apply {
                add(fetchButton)
                add(exportButton)
            }
            add(buttonPanel, BorderLayout.EAST)
        }
        add(headerPanel, BorderLayout.NORTH)

        // Table setup
        tableModel.addColumn("Rank")
        tableModel.addColumn("Ticker")
        tableModel.addColumn("Description")
        tableModel.addColumn("Open Interest")
        tableModel.addColumn("Volume")
        tableModel.addColumn("Yes %")
        tableModel.addColumn("Bid")
        tableModel.addColumn("Ask")

        table.apply {
            autoResizeMode = JTable.AUTO_RESIZE_ALL_COLUMNS
            columnModel.getColumn(0).preferredWidth = 50
            columnModel.getColumn(1).preferredWidth = 100
            columnModel.getColumn(2).preferredWidth = 350
            columnModel.getColumn(3).preferredWidth = 100
            columnModel.getColumn(4).preferredWidth = 80
            columnModel.getColumn(5).preferredWidth = 60
            columnModel.getColumn(6).preferredWidth = 60
            columnModel.getColumn(7).preferredWidth = 60
        }

        val tableScroll = JScrollPane(table)
        add(tableScroll, BorderLayout.CENTER)

        // Bottom panel with progress and status
        val bottomPanel = JPanel(BorderLayout()).apply {
            border = BorderFactory.createEmptyBorder(5, 10, 10, 10)

            progressArea.apply {
                isEditable = false
                font = Font("Monospaced", Font.PLAIN, 12)
            }
            val progressScroll = JScrollPane(progressArea).apply {
                preferredSize = Dimension(0, 120)
            }
            add(progressScroll, BorderLayout.CENTER)

            statusLabel.apply {
                border = BorderFactory.createEmptyBorder(5, 0, 0, 0)
            }
            add(statusLabel, BorderLayout.SOUTH)
        }
        add(bottomPanel, BorderLayout.SOUTH)

        exportButton.isEnabled = false
        setLocationRelativeTo(null)
    }

    private fun setupActions() {
        fetchButton.addActionListener {
            fetchMarkets()
        }

        exportButton.addActionListener {
            exportToCsv()
        }
    }

    private fun fetchMarkets() {
        fetchButton.isEnabled = false
        exportButton.isEnabled = false
        tableModel.rowCount = 0
        progressArea.text = ""
        statusLabel.text = "Fetching..."

        Thread {
            try {
                markets = scraper.fetchMarkets { message ->
                    SwingUtilities.invokeLater {
                        progressArea.append("$message\n")
                        progressArea.caretPosition = progressArea.document.length
                    }
                }

                SwingUtilities.invokeLater {
                    populateTable()
                    statusLabel.text = "Loaded ${markets.size} markets"
                    fetchButton.isEnabled = true
                    exportButton.isEnabled = markets.isNotEmpty()
                }
            } catch (e: Exception) {
                SwingUtilities.invokeLater {
                    progressArea.append("Error: ${e.message}\n")
                    statusLabel.text = "Error occurred"
                    fetchButton.isEnabled = true
                }
            }
        }.start()
    }

    private fun populateTable() {
        tableModel.rowCount = 0
        markets.forEachIndexed { index, market ->
            val probability = scraper.calcProbability(market)
            val desc = buildString {
                append(market.title)
                if (market.subtitle.isNotEmpty()) {
                    append(" - ${market.subtitle}")
                }
            }
            tableModel.addRow(arrayOf(
                index + 1,
                market.ticker,
                desc,
                "%,d".format(market.openInterest),
                "%,d".format(market.volume),
                probability?.let { "${it}%" } ?: "N/A",
                market.yesBid,
                market.yesAsk
            ))
        }
    }

    private fun exportToCsv() {
        val fileChooser = JFileChooser().apply {
            selectedFile = File("kalshi_public_markets.csv")
        }

        if (fileChooser.showSaveDialog(this) == JFileChooser.APPROVE_OPTION) {
            try {
                FileWriter(fileChooser.selectedFile).use { writer ->
                    writer.write("rank,ticker,description,open_interest,volume,yes_probability,yes_bid,yes_ask,close_time\n")
                    markets.forEachIndexed { index, market ->
                        val probability = scraper.calcProbability(market)
                        val desc = buildString {
                            append(market.title)
                            if (market.subtitle.isNotEmpty()) {
                                append(" - ${market.subtitle}")
                            }
                        }.replace("\"", "\"\"")

                        writer.write("${index + 1},${market.ticker},\"$desc\",${market.openInterest},${market.volume},${probability ?: ""},${market.yesBid},${market.yesAsk},${market.closeTime}\n")
                    }
                }
                statusLabel.text = "Exported to ${fileChooser.selectedFile.name}"
                JOptionPane.showMessageDialog(this, "Exported successfully!", "Export", JOptionPane.INFORMATION_MESSAGE)
            } catch (e: Exception) {
                JOptionPane.showMessageDialog(this, "Export failed: ${e.message}", "Error", JOptionPane.ERROR_MESSAGE)
            }
        }
    }
}
