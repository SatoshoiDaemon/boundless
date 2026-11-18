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

/** Keeps AWCAPI's single broad collision walk while avoiding a temporary AABB for each shape. */
@Mixin(targets = "com.nyfaria.awcapi.entity.ClimberComponent", remap = false)
@Pseudo
public abstract class ClimberComponentCollisionScanMixin {
    @Unique
    private static final Direction[] boundless$directions = {
            Direction.DOWN, Direction.UP, Direction.NORTH,
            Direction.SOUTH, Direction.WEST, Direction.EAST
    };

    @Shadow @Final private Mob mob;
    @Shadow @Final private double[] facingDistances;
    @Shadow private Pair<Direction, Vec3> groundDirection;

    @Shadow
    private void forEachCollisonBox(AABB aabb, Shapes.DoubleLineConsumer action) {
    }

    @Unique private final double[] boundless$fallbackDistances = new double[6];

    /**
     * @author Boundless
     * @reason AWCAPI already gathers collision shapes once for all six directions. Reuse that
     * broad-phase walk and calculate both of its distance passes from primitive box coordinates.
     */
    @Overwrite
    private void updateWalkingSide() {
        AABB entityBox = mob.getBoundingBox();
        AABB inflatedEntityBox = entityBox.inflate(0.2f);
        float stickingDistance = mob.zza != 0 ? 1.5f : 0.1f;
        AABB scanBox = inflatedEntityBox.inflate(stickingDistance);

        for (Direction direction : boundless$directions) {
            facingDistances[direction.ordinal()] = Double.MAX_VALUE;
            boundless$fallbackDistances[direction.ordinal()] = Double.MAX_VALUE;
        }

        forEachCollisonBox(scanBox, (minX, minY, minZ, maxX, maxY, maxZ) ->
                boundless$accumulateFacingDistances(
                        entityBox, inflatedEntityBox, stickingDistance,
                        minX, minY, minZ, maxX, maxY, maxZ));

        boolean hasPrimaryFacing = false;
        for (Direction direction : boundless$directions) {
            if (facingDistances[direction.ordinal()] < stickingDistance - 1.0E-6D) {
                hasPrimaryFacing = true;
                break;
            }
        }

        double closestFacingDistance = Double.MAX_VALUE;
        Direction closestFacing = null;
        double weightX = 0.0D;
        double weightY = 0.0D;
        double weightZ = 0.0D;
        double[] distances = hasPrimaryFacing ? facingDistances : boundless$fallbackDistances;

        for (Direction direction : boundless$directions) {
            double closestDistance = distances[direction.ordinal()];
            if (closestDistance < closestFacingDistance) {
                closestFacingDistance = closestDistance;
                closestFacing = direction;
            }

            if (closestDistance < Double.MAX_VALUE) {
                double weight = 1.0D - Math.min(closestDistance, stickingDistance) / stickingDistance;
                weightX += direction.getStepX() * weight;
                weightY += direction.getStepY() * weight;
                weightZ += direction.getStepZ() * weight;
            }
        }

        if (closestFacing == null) {
            groundDirection = Pair.of(Direction.DOWN, new Vec3(0.0D, -1.0D, 0.0D));
        } else {
            Vec3 weighting = new Vec3(weightX, weightY, weightZ);
            groundDirection = Pair.of(
                    closestFacing,
                    weighting.normalize().add(0.0D, -0.001f, 0.0D).normalize());
        }
    }

    @Unique
    private void boundless$accumulateFacingDistances(
            AABB entityBox,
            AABB inflatedEntityBox,
            float stickingDistance,
            double minX,
            double minY,
            double minZ,
            double maxX,
            double maxY,
            double maxZ) {
        for (Direction direction : boundless$directions) {
            if (!boundless$intersectsFacingSearchBox(
                    inflatedEntityBox, direction, stickingDistance,
                    minX, minY, minZ, maxX, maxY, maxZ)) {
                continue;
            }

            int index = direction.ordinal();
            double offset = -direction.getStepX() * stickingDistance;
            if (direction.getAxis() == Direction.Axis.Y) {
                offset = -direction.getStepY() * stickingDistance;
                facingDistances[index] = Math.min(facingDistances[index], Math.abs(
                        boundless$calculateYOffset(entityBox, minX, minY, minZ, maxX, maxY, maxZ,
                                offset, 0.0D)));
                boundless$fallbackDistances[index] = Math.min(boundless$fallbackDistances[index], Math.abs(
                        boundless$calculateYOffset(entityBox, minX, minY, minZ, maxX, maxY, maxZ,
                                offset, 0.2D)));
            } else if (direction.getAxis() == Direction.Axis.Z) {
                offset = -direction.getStepZ() * stickingDistance;
                facingDistances[index] = Math.min(facingDistances[index], Math.abs(
                        boundless$calculateZOffset(entityBox, minX, minY, minZ, maxX, maxY, maxZ,
                                offset, 0.0D)));
                boundless$fallbackDistances[index] = Math.min(boundless$fallbackDistances[index], Math.abs(
                        boundless$calculateZOffset(entityBox, minX, minY, minZ, maxX, maxY, maxZ,
                                offset, 0.2D)));
            } else {
                facingDistances[index] = Math.min(facingDistances[index], Math.abs(
                        boundless$calculateXOffset(entityBox, minX, minY, minZ, maxX, maxY, maxZ,
                                offset, 0.0D)));
                boundless$fallbackDistances[index] = Math.min(boundless$fallbackDistances[index], Math.abs(
                        boundless$calculateXOffset(entityBox, minX, minY, minZ, maxX, maxY, maxZ,
                                offset, 0.2D)));
            }
        }
    }

    @Unique
    private static boolean boundless$intersectsFacingSearchBox(
            AABB box,
            Direction direction,
            float stickingDistance,
            double minX,
            double minY,
            double minZ,
            double maxX,
            double maxY,
            double maxZ) {
        int stepX = direction.getStepX();
        int stepY = direction.getStepY();
        int stepZ = direction.getStepZ();
        double searchMinX = box.minX + (stepX < 0 ? stepX * stickingDistance : 0.0F);
        double searchMinY = box.minY + (stepY < 0 ? stepY * stickingDistance : 0.0F);
        double searchMinZ = box.minZ + (stepZ < 0 ? stepZ * stickingDistance : 0.0F);
        double searchMaxX = box.maxX + (stepX > 0 ? stepX * stickingDistance : 0.0F);
        double searchMaxY = box.maxY + (stepY > 0 ? stepY * stickingDistance : 0.0F);
        double searchMaxZ = box.maxZ + (stepZ > 0 ? stepZ * stickingDistance : 0.0F);

        return maxX > searchMinX && minX < searchMaxX
                && maxY > searchMinY && minY < searchMaxY
                && maxZ > searchMinZ && minZ < searchMaxZ;
    }

    @Unique
    private static double boundless$calculateXOffset(
            AABB box,
            double minX,
            double minY,
            double minZ,
            double maxX,
            double maxY,
            double maxZ,
            double offset,
            double expand) {
        if (maxY > box.minY - expand && minY < box.maxY + expand
                && maxZ > box.minZ - expand && minZ < box.maxZ + expand) {
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
    private static double boundless$calculateYOffset(
            AABB box,
            double minX,
            double minY,
            double minZ,
            double maxX,
            double maxY,
            double maxZ,
            double offset,
            double expand) {
        if (maxX > box.minX - expand && minX < box.maxX + expand
                && maxZ > box.minZ - expand && minZ < box.maxZ + expand) {
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
    private static double boundless$calculateZOffset(
            AABB box,
            double minX,
            double minY,
            double minZ,
            double maxX,
            double maxY,
            double maxZ,
            double offset,
            double expand) {
        if (maxX > box.minX - expand && minX < box.maxX + expand
                && maxY > box.minY - expand && minY < box.maxY + expand) {
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
