# Boundless Chunk Utils

Forge 1.20.1 patch for Better Chunk Loading 1.20.1-5.4. It deduplicates pending chunk post-processing entries per dimension on the server thread, clears the keys after each server tick, and falls back to the original queue behavior if the optional integration cannot read a chunk entry. The patch is version-gated and does nothing with other Better Chunk Loading builds.
