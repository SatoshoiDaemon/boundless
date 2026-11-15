package com.satoshoidaemon.boundlessfix;

import net.minecraft.world.entity.MobCategory;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class IllageProjectileCategoryFixTest {
    @Test
    void onlyEnablesForTheObservedIllageVersion() {
        assertTrue(IllageProjectileCategoryFix.supports("illageandspillage", "1.2.8"));
        assertFalse(IllageProjectileCategoryFix.supports("illageandspillage", "1.2.9"));
        assertFalse(IllageProjectileCategoryFix.supports("anothermod", "1.2.8"));
    }

    @Test
    void classifiesBoneAndAxeAsMiscProjectiles() {
        assertEquals(MobCategory.MISC,
                IllageProjectileCategoryFix.category("bone", MobCategory.MONSTER));
        assertEquals(MobCategory.MISC,
                IllageProjectileCategoryFix.category("axe", MobCategory.MONSTER));
    }

    @Test
    void preservesAllOtherEntityCategories() {
        assertEquals(MobCategory.MONSTER,
                IllageProjectileCategoryFix.category("funnybone", MobCategory.MONSTER));
        assertEquals(MobCategory.MISC,
                IllageProjectileCategoryFix.category("bone", MobCategory.MISC));
    }
}
