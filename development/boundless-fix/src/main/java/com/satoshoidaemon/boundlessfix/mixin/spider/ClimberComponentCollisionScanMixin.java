package com.satoshoidaemon.boundlessfix.mixin.spider;

import net.minecraft.core.Direction;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.Shapes;
import org.apache.commons.lang3.tuple.Pair;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Overwrite;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;

/** Removes the per-facing lists and AABBs built by AWCAPI's spider tick collision scan. */
@Mixin(targets = "com.nyfaria.awcapi.entity.ClimberComponent", remap = false)
@Pseudo
public abstract class ClimberComponentCollisionScanMixin {
    @Shadow @Final private Mob mob;

    @Shadow
    private void forEachCollisonBox(AABB aabb, Shapes.DoubleLineConsumer action) {
    }

    @Shadow private Pair<Direction, Vec3> groundDirection;

    @Unique private double boundlessFix$closestDistance;

    /**
     * @author Boundless
     * @reason AWCAPI materializes six temporary lists and an AABB per block shape on every spider tick.
     */
    @Overwrite
    private void updateWalkingSide() {
        AABB entityBox = mob.getBoundingBox();
        AABB inflatedEntityBox = entityBox.inflate(0.2f);
        double closestFacingDistance = Double.MAX_VALUE;
        Direction closestFacing = null;
        double weightX = 0.0;
        double weightY = 0.0;
        double weightZ = 0.0;
        float stickingDistance = mob.zza != 0 ? 1.5f : 0.1f;

        for (Direction facing : Direction.values()) {
            boundlessFix$closestDistance = Double.MAX_VALUE;
            AABB searchBox = inflatedEntityBox.expandTowards(
                    facing.getStepX() * stickingDistance,
                    facing.getStepY() * stickingDistance,
                    facing.getStepZ() * stickingDistance);

            forEachCollisonBox(searchBox, (minX, minY, minZ, maxX, maxY, maxZ) -> {
                double offset = switch (facing.getAxis()) {
                    case X -> boundlessFix$calculateXOffset(entityBox, minX, minY, minZ, maxX, maxY, maxZ,
                            -facing.getStepX() * stickingDistance);
                    case Y -> boundlessFix$calculateYOffset(entityBox, minX, minY, minZ, maxX, maxY, maxZ,
                            -facing.getStepY() * stickingDistance);
                    case Z -> boundlessFix$calculateZOffset(entityBox, minX, minY, minZ, maxX, maxY, maxZ,
                            -facing.getStepZ() * stickingDistance);
                };
                boundlessFix$closestDistance = Math.min(boundlessFix$closestDistance, Math.abs(offset));
            });

            double closestDistance = boundlessFix$closestDistance;
            if (closestDistance < closestFacingDistance) {
                closestFacingDistance = closestDistance;
                closestFacing = facing;
            }

            if (closestDistance < Double.MAX_VALUE) {
                double weight = 1.0 - Math.min(closestDistance, stickingDistance) / stickingDistance;
                weightX += facing.getStepX() * weight;
                weightY += facing.getStepY() * weight;
                weightZ += facing.getStepZ() * weight;
            }
        }

        if (closestFacing == null) {
            groundDirection = Pair.of(Direction.DOWN, new Vec3(0, -1, 0));
        } else {
            Vec3 weighting = new Vec3(weightX, weightY, weightZ);
            groundDirection = Pair.of(closestFacing, weighting.normalize().add(0, -0.001f, 0).normalize());
        }
    }

    @Unique
    private static double boundlessFix$calculateXOffset(AABB box, double minX, double minY, double minZ,
                                                         double maxX, double maxY, double maxZ, double offset) {
        if (maxY > box.minY && minY < box.maxY && maxZ > box.minZ && minZ < box.maxZ) {
            if (offset > 0.0D && maxX <= box.minX) {
                double distance = box.minX - maxX;
                if (distance < offset) offset = distance;
            } else if (offset < 0.0D && minX >= box.maxX) {
                double distance = box.maxX - minX;
                if (distance > offset) offset = distance;
            }
        }
        return offset;
    }

    @Unique
    private static double boundlessFix$calculateYOffset(AABB box, double minX, double minY, double minZ,
                                                         double maxX, double maxY, double maxZ, double offset) {
        if (maxX > box.minX && minX < box.maxX && maxZ > box.minZ && minZ < box.maxZ) {
            if (offset > 0.0D && maxY <= box.minY) {
                double distance = box.minY - maxY;
                if (distance < offset) offset = distance;
            } else if (offset < 0.0D && minY >= box.maxY) {
                double distance = box.maxY - minY;
                if (distance > offset) offset = distance;
            }
        }
        return offset;
    }

    @Unique
    private static double boundlessFix$calculateZOffset(AABB box, double minX, double minY, double minZ,
                                                         double maxX, double maxY, double maxZ, double offset) {
        if (maxX > box.minX && minX < box.maxX && maxY > box.minY && minY < box.maxY) {
            if (offset > 0.0D && maxZ <= box.minZ) {
                double distance = box.minZ - maxZ;
                if (distance < offset) offset = distance;
            } else if (offset < 0.0D && minZ >= box.maxZ) {
                double distance = box.maxZ - minZ;
                if (distance > offset) offset = distance;
            }
        }
        return offset;
    }
}
