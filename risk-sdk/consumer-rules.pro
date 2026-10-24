# Consumer Proguard rules for risk-sdk
-keep class com.raksham.risk.model.** { *; }
-keepclassmembers class * {
    @kotlinx.serialization.Serializable *;
}
