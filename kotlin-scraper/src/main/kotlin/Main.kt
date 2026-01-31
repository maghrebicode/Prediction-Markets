package kalshi

import javax.swing.SwingUtilities
import javax.swing.UIManager

fun main() {
    // Set system look and feel for native appearance
    try {
        UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName())
    } catch (e: Exception) {
        // Fall back to default look and feel
    }

    SwingUtilities.invokeLater {
        MainUI().isVisible = true
    }
}
