allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
subprojects {
    project.evaluationDependsOn(":app")
}

subprojects {
    val configureNamespace = Action<Project> {
        if (plugins.hasPlugin("com.android.application") ||
            plugins.hasPlugin("com.android.library")) {
            val android = extensions.findByName("android")
            if (android != null) {
                val baseExtension = android as? com.android.build.gradle.BaseExtension
                if (baseExtension != null) {
                    baseExtension.compileSdkVersion(36)
                    if (baseExtension.namespace == null) {
                        val manifestFile = file("src/main/AndroidManifest.xml")
                        if (manifestFile.exists()) {
                            val manifestXml = manifestFile.readText()
                            val matcher = java.util.regex.Pattern.compile("package=\"([^\"]+)\"").matcher(manifestXml)
                            if (matcher.find()) {
                                baseExtension.namespace = matcher.group(1)
                            }
                        }
                    }
                }
            }
        }
    }
    
    if (state.executed) {
        configureNamespace.execute(this)
    } else {
        afterEvaluate(configureNamespace)
    }
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
