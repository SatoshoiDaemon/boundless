package local.combatrollhudfix.mixin;

import com.mojang.blaze3d.vertex.PoseStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/** Preserves the root matrix when AutoHUD cleans up a canceled overlay. */
@Pseudo
@Mixin(targets = "mod.crend.autohud.render.AutoHudRenderLayer$DoMove", remap = false)
public abstract class AutoHudMoveMixin {
    @Unique private static boolean localhudfix$reported;

    @Redirect(method = "doPostRender", at = @At(value = "INVOKE",
            target = "Lcom/mojang/blaze3d/vertex/PoseStack;m_85849_()V"),
            remap = false, require = 1)
    private void localhudfix$preserveRoot(PoseStack poses) {
        if (!poses.m_85851_()) {
            poses.m_85849_();
        } else if (!localhudfix$reported) {
            localhudfix$reported = true;
            System.err.println("[HUD Compatibility Fix] Prevented AutoHUD from removing the GUI root matrix; HUDs remain enabled.");
        }
    }
}
