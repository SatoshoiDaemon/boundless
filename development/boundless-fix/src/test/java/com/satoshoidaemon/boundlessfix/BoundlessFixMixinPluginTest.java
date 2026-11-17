package com.satoshoidaemon.boundlessfix;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BoundlessFixMixinPluginTest {
    @Test
    void appliesNonOptionalMixinsWithoutAnIllageLookup() {
        BoundlessFixMixinPlugin plugin = new BoundlessFixMixinPlugin();

        assertTrue(plugin.shouldApplyMixin("some.Target", "some.OtherMixin"));
    }

    @Test
    void skipsIllageMixinSafelyBeforeForgeCreatesTheLoadingList() {
        assertFalse(BoundlessFixMixinPlugin.shouldApplyIllageMixin(null));
    }

    @Test
    void onlyTargetsTheBundledAwcapiVersionWhoseCollisionCodeWasReplaced() {
        assertTrue(ClimberCollisionOptimization.supports("awcapi", "1.0.3"));
        assertFalse(ClimberCollisionOptimization.supports("awcapi", "1.0.2"));
        assertFalse(ClimberCollisionOptimization.supports("anothermod", "1.0.3"));
    }
}
