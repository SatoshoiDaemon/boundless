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
}
