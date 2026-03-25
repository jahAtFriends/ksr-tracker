plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "org.friends.ksrtracker"
    compileSdk = 35

    defaultConfig {
        applicationId = "org.friends.ksrtracker"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        buildConfigField("String", "TRACKER_BASE_URL", "\"http://172.50.1.56:8000\"")
        buildConfigField("String", "TRACKER_DEVICE_KEY", "\"abc123\"")
        buildConfigField("String", "TRACKER_DEVICE_KEYS_JSON", "\"{\\\"tracker-1\\\":\\\"abc123\\\",\\\"tracker-2\\\":\\\"abc123\\\"}\"")
        buildConfigField("String", "TRACKER_DEVICE_IDS_CSV", "\"tracker-1,tracker-2\"")
        buildConfigField("String", "TRACKER_SESSION_ID", "\"race-2026\"")
        buildConfigField("long", "LOCATION_INTERVAL_MS", "5000L")
        buildConfigField("long", "LOCATION_FASTEST_MS", "2500L")
        buildConfigField("int", "UPLOAD_BATCH_SIZE", "1")
    }

    buildTypes {
        debug {
            isMinifyEnabled = false
        }
        release {
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        buildConfig = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-ktx:1.10.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("com.google.android.material:material:1.13.0")
    implementation("com.google.android.gms:play-services-location:21.3.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")

    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
}
