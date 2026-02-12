# Add project specific ProGuard rules here.
# By default, the flags in this file are appended to flags specified
# in the Android SDK tools.

# Keep serialization classes
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.AnnotationsKt

-keepclassmembers class kotlinx.serialization.json.** {
    *** Companion;
}
-keepclasseswithmembers class kotlinx.serialization.json.** {
    kotlinx.serialization.KSerializer serializer(...);
}

-keep,includedescriptorclasses class com.predictionmarkets.scraper.**$$serializer { *; }
-keepclassmembers class com.predictionmarkets.scraper.** {
    *** Companion;
}
-keepclasseswithmembers class com.predictionmarkets.scraper.** {
    kotlinx.serialization.KSerializer serializer(...);
}
