# Boundless Fix

Boundless Fix contains narrow corrections for the versions in the Boundless pack. It does not require either corrected mod as a mandatory dependency.

## Dayzombie Rebooted 1.0.5

Dayzombie Rebooted reads `config/dayzombiesconfig` without a file extension. Boundless has a user-edited `config/dayzombiesconfig.json`, which the mod does not read and which led to repeated `FileNotFoundException` stack traces during spawn checks. At mod construction, Boundless Fix creates the expected file only when Dayzombie is loaded and the file is missing. It copies the existing `.json` settings first, then the bundled default. It never replaces an existing extensionless file.

## Illage and Spillage: Respillaged 1.2.8

The `bone` and `axe` entity factories register projectile classes (`AbstractHurtingProjectile`) with `MobCategory.MONSTER`. Forge 47.4.28's `DefaultAttributes.validate()` excludes `MobCategory.MISC` from its mob-attribute check, so those two projectiles produced repeated missing-attributes errors each time the attribute registry was validated. A version-gated mixin changes only those two projectile categories to `MISC`; it leaves their entity classes, launch behavior, and all other entity categories intact. The patch is enabled only for mod ID `illageandspillage`, version `1.2.8`.

## Build and verification

Use JDK 17 and run `gradlew.bat test build`. The distributable artifact is `build/libs/boundlessfix-0.1.0.jar`. Tests cover the Dayzombie file-preservation/copy/fallback behavior and the Illage version/category gate. Forge build verification confirms the mixin config and generated refmap are packaged. Runtime log verification still requires a fresh game launch with this JAR; the existing log predates it.
