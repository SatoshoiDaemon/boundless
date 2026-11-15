# Performance capture: p0.2-fullpack-xmx6-20261115

- Scenario: `None`
- Commit: `unknown`
- Status: `None`

## Startup and world loading

- Loaded runtime mods: n/d
- Minecraft startup timer: n/d s
- First main menu signal: n/d s from launch
- Human menu-ready mark: n/d s from capture start
- Integrated server start: n/d s from launch
- World `Done` marker: n/d s from launch
- Human world-ready mark: n/d s from capture start
- Spawn progress: n/d% to n/d% in n/d s


## CPU and memory

- No CPU or memory time series found.

## Frametime

- No PresentMon frame CSV found.

## Tick backlog and JFR

- Log backlog warnings: n/d; mean/p95/p99/max n/d/n/d/n/d/n/d ms. These are accumulated delays between warnings, not individual MSPT.
- JFR ServerTickTime window averages: n=0, mean/p95/p99/max n/d/n/d/n/d/n/d ms.
- GC pause sum from GarbageCollection events: 16.91 s; GC event count 323.
- JFR chunk-generation events: 0.
- JFR execution samples for thread `DFU cleaning thread`: n=1; most frequent stack frames: java/util/concurrent/ConcurrentHashMap.clear, org.embeddedt.modernfix.dfu.DFUBlaster$CleanerThread$$Lambda$48718+0x000002159a3f9810/118423064.accept, java/util/ArrayList.forEach, org/embeddedt/modernfix/dfu/DFUBlaster$CleanerThread.run.
- JFR execution samples for thread `Datafixer Bootstrap`: n=159; most frequent stack frames: it/unimi/dsi/fastutil/longs/Long2ObjectMaps$SynchronizedMap.computeIfAbsent, com/mojang/datafixers/TypeRewriteRule$Seq.cap1, it/unimi/dsi/fastutil/longs/Long2ObjectOpenHashMap.computeIfAbsent, com/mojang/datafixers/TypeRewriteRule$Seq.rewrite, com/mojang/datafixers/DataFixerUpper.lambda$getRule$1.
- JFR execution samples for thread `EuphoriaConfigWatcher`: n=1; most frequent stack frames: com/euphoriapatches/euphoria_patcher/config/Config.lambda$startConfigWatcher$1, com.euphoriapatches.euphoria_patcher.config.Config$$Lambda$1543+0x000002159474bdf0/599594742.run, java/util/concurrent/Executors$RunnableAdapter.call, java/util/concurrent/FutureTask.runAndReset, java/util/concurrent/ScheduledThreadPoolExecutor$ScheduledFutureTask.run.
- JFR execution samples for thread `FancyMenu-WebUtils-ConnectivityCheck-1`: n=6; most frequent stack frames: sun/security/util/math/intpoly/IntegerPolynomial$MutableElement.setProduct, sun/security/ec/ECOperations.setDouble, sun/security/ec/ECOperations.double4, sun/security/util/math/intpoly/IntegerPolynomial$MutableElement.setSquare, sun/security/util/math/intpoly/IntegerPolynomialP384.mult.
- JFR execution samples for thread `Forge Version Check`: n=3; most frequent stack frames: java/util/TreeSet.<init>, jdk/internal/net/http/hpack/Encoder.header, java/util/concurrent/CompletableFuture.uniHandleStage, java/util/concurrent/CompletableFuture.handle, jdk/internal/net/http/ExchangeImpl.get.
- JFR execution samples for thread `ForkJoinPool.commonPool-worker-1`: n=3; most frequent stack frames: java/nio/file/FileTreeWalker.getAttributes, java/nio/file/FileTreeWalker.visit, java/nio/file/FileTreeWalker.next, java/nio/file/Files.walkFileTree, jdk/internal/jimage/ImageReader$SharedImageReader.visitLocation.
- JFR execution samples for thread `ForkJoinPool.commonPool-worker-3`: n=3; most frequent stack frames: java/math/BigInteger.oddModPow, java/math/BigInteger.implMultiplyToLen, java/math/BigInteger.multiplyToLen, java/math/BigInteger.implMontgomeryMultiply, java/math/BigInteger.montgomeryMultiply.
- JFR execution samples for thread `GML Mappings Thread`: n=36; most frequent stack frames: net/minecraftforge/srgutils/InternalUtils.loadNamed, net/minecraftforge/srgutils/InternalUtils.load, net/minecraftforge/srgutils/InternalUtils.loadProguard, java/lang/String.split, net/minecraftforge/srgutils/IMappingFile.load.
- JFR execution samples for thread `HttpClient-1-Worker-0`: n=4; most frequent stack frames: sun/security/util/math/intpoly/IntegerPolynomial$MutableElement.setProduct, java/lang/Character.digit, sun/security/util/math/intpoly/IntegerPolynomial25519.carryReduce, sun/security/util/math/intpoly/IntegerPolynomial25519.mult, sun/security/ec/XECOperations.pointMultiply.
- JFR execution samples for thread `HttpClient-2-Worker-0`: n=1; most frequent stack frames: sun/security/util/math/intpoly/IntegerPolynomial$MutableElement.setProduct, sun/security/util/math/intpoly/IntegerPolynomialP256.mult, sun/security/ec/ECOperations.setDouble, sun/security/ec/ECOperations.double4.
- JFR execution samples for thread `HttpClient-2-Worker-1`: n=2; most frequent stack frames: sun/security/util/math/intpoly/IntegerPolynomial$MutableElement.setProduct, sun/security/util/math/intpoly/IntegerPolynomialP384.mult, sun/security/ec/ECOperations.setDouble, sun/security/ec/ECOperations.double4, sun/security/ec/XECOperations.cswap.
- JFR execution samples for thread `IO-Worker-2`: n=1; most frequent stack frames: org/lwjgl/openal/ALUtil.getStringList, com/mojang/blaze3d/audio/Library.m_193468_, com/mojang/blaze3d/audio/Library.m_193474_, net/minecraft/client/sounds/SoundEngine.m_194505_, net.minecraft.client.sounds.SoundEngine$$Lambda$47828+0x000002159a2eb9b8/1015824134.run.
- JFR execution samples for thread `Java Sound Event Dispatcher`: n=2; most frequent stack frames: com/sun/media/sound/EventDispatcher.dispatchEvents, com/sun/media/sound/EventDispatcher.run, java/lang/Thread.run, com/sun/media/sound/EventDispatcher.monitorLines.
- JFR execution samples for thread `Keep-Alive-Timer`: n=1; most frequent stack frames: sun/nio/ch/Net.getSocketOption, sun/nio/ch/NioSocketImpl.getOption, java/net/DelegatingSocketImpl.getOption, java/net/Socket.getSoLinger.
- JFR execution samples for thread `LauncherLogger-Worker`: n=2; most frequent stack frames: java/util/concurrent/LinkedBlockingQueue.poll, dev/kostromdan/mods/crash_assistant/common_config/loading_utils/LauncherLogger$AsyncLogWriter.run.
- JFR execution samples for thread `NativeInitializationThread`: n=2; most frequent stack frames: cpw.mods.jarhandling.impl.Jar$$Lambda$164+0x000002159408df98/1199262943.apply, java/util/Optional.map, cpw/mods/jarhandling/impl/Jar.findFile, cpw/mods/jarhandling/impl/Jar$JarModuleDataProvider.findFile, cpw/mods/cl/ModuleClassLoader.lambda$findResourceList$14.
- JFR execution samples for thread `Placebo Patreon Wing Loader`: n=1; most frequent stack frames: sun/security/util/math/intpoly/IntegerPolynomial$MutableElement.setProduct, sun/security/ec/ECOperations.setDouble, sun/security/ec/ECOperations.double4, sun/security/ec/ECOperations.multiply.
- JFR execution samples for thread `ReactiveMusic Player Thread`: n=7683; most frequent stack frames: circuitlord/reactivemusic/PlayerThread.run, rm_javazoom/jl/decoder/LayerIIIDecoder.decode, rm_javazoom/jl/decoder/LayerIIIDecoder.decodeFrame, rm_javazoom/jl/decoder/Decoder.decodeFrame, rm_javazoom/jl/player/advanced/AdvancedPlayer.decodeFrame.
- JFR execution samples for thread `Thread-22`: n=1; most frequent stack frames: de/keksuccino/konkrete/sound/SoundHandler.lambda$init$0, de.keksuccino.konkrete.sound.SoundHandler$$Lambda$52335+0x000002159a80bfb8/1763275935.run, java/lang/Thread.run.
- JFR execution samples for thread `Thread-23`: n=2; most frequent stack frames: xaero/map/MapRunner.run, java/lang/Thread.run.
- JFR execution samples for thread `Thread-9`: n=16; most frequent stack frames: com/electronwill/nightconfig/core/file/FileWatcher$WatcherThread.run, java/util/concurrent/locks/AbstractQueuedSynchronizer.signalNext, java/util/concurrent/locks/AbstractQueuedSynchronizer.release, java/util/concurrent/locks/ReentrantLock.unlock, java/util/concurrent/LinkedBlockingDeque.pollFirst.
- JFR execution samples for thread `Worker-Main-1`: n=175; most frequent stack frames: net/minecraft/client/gui/font/FontManager.m_283966_, net.minecraft.client.gui.font.FontManager$$Lambda$48054+0x000002159a31ae28/842291848.accept, it/unimi/dsi/fastutil/ints/IntOpenHashSet.forEach, net/minecraft/client/gui/font/CodepointMap.m_284412_, net/minecraft/client/gui/font/providers/BitmapProvider.m_214022_.
- JFR execution samples for thread `Worker-ResourceReload-0`: n=696; most frequent stack frames: java/util/zip/ZipFile.getZipEntry, java/util/zip/ZipFile$ZipEntryIterator.next, java/util/zip/ZipFile$ZipEntryIterator.nextElement, me/jellysquid/mods/sodium/client/util/color/ColorSRGB.linearToSrgb, net/minecraft/server/packs/FilePackResources.m_8031_.
- JFR execution samples for thread `Worker-ResourceReload-1`: n=3111; most frequent stack frames: java/util/Objects.equals, java/util/HashMap.getNode, it/unimi/dsi/fastutil/objects/ObjectOpenCustomHashSet.addOrGet, net/minecraft/client/renderer/block/BlockModelShaper.m_110889_, net/minecraftforge/client/model/ElementsModel.addQuads.
- JFR execution samples for thread `Worker-ResourceReload-2`: n=438; most frequent stack frames: java/util/zip/ZipFile$ZipEntryIterator.nextElement, java/util/zip/ZipFile.getZipEntry, java/util/zip/ZipFile$ZipEntryIterator.next, net/minecraft/server/packs/FilePackResources.m_8031_, me/jellysquid/mods/sodium/client/util/color/ColorSRGB.linearToSrgb.
- JFR execution samples for thread `main`: n=3519; most frequent stack frames: java/lang/module/Resolver.finish, java/util/HashMap.getNode, java/lang/module/Configuration.<init>, java/lang/module/Resolver.makeGraph, java/util/HashMap.containsKey.
- JFR execution samples for thread `modloading-worker-0`: n=441; most frequent stack frames: java/util/HashMap.getNode, cpw/mods/jarhandling/impl/Jar.findFile, java/util/HashMap.containsKey, cpw.mods.jarhandling.impl.Jar$$Lambda$164+0x000002159408df98/1199262943.apply, java/util/Optional.map.
- JFR execution samples for thread `pool-14-thread-1`: n=1; most frequent stack frames: com/corosus/watut/client/screen/ByteBufferProcessor.lambda$startProcessing$0, com.corosus.watut.client.screen.ByteBufferProcessor$$Lambda$57155+0x000002159aefc5a8/1094506629.run, java/util/concurrent/Executors$RunnableAdapter.call, java/util/concurrent/FutureTask.run, java/util/concurrent/ThreadPoolExecutor.runWorker.
- JFR execution samples for thread `pool-2-thread-1`: n=13; most frequent stack frames: java/util/concurrent/ScheduledThreadPoolExecutor$DelayedWorkQueue.take, java/util/concurrent/ThreadPoolExecutor.runWorker, java/util/concurrent/ThreadPoolExecutor$Worker.run, java/lang/Thread.run, org/lwjgl/opengl/GL.createCapabilities.
- JFR execution samples for thread `pool-3-thread-1`: n=94; most frequent stack frames: org/objectweb/asm/ClassReader.accept, net/minecraftforge/fml/loading/moddiscovery/Scanner.fileVisitor, net/minecraftforge/fml/loading/moddiscovery/Scanner.lambda$scan$0, org/objectweb/asm/ClassReader.<init>, org/objectweb/asm/ClassReader.readMethod.
- JFR execution samples for thread `pool-4-thread-1`: n=255; most frequent stack frames: org/spongepowered/asm/util/Bytecode.getOpcodeName, org/spongepowered/asm/mixin/transformer/ClassInfo.findInHierarchy, org/spongepowered/asm/mixin/transformer/ClassInfo.findMember, java/lang/Class.copyFields, java/lang/Class.getDeclaredFields.
- JFR execution samples for thread `pool-6-thread-1`: n=133; most frequent stack frames: java/util/regex/Pattern$GroupHead.match, net/mehvahdjukaar/moonlight/api/resources/BlockTypeResTransformer.replaceFullGenericType, java/util/regex/Pattern.compile, java/util/regex/Pattern$BmpCharProperty.match, java/util/regex/Pattern$Curly.match1.
- JFR execution samples for thread `pool-6-thread-3`: n=2; most frequent stack frames: net/mehvahdjukaar/moonlight/api/resources/textures/TextureCollager.apply, net/mehvahdjukaar/moonlight/api/resources/textures/TextureOps.createScaled, net/mehvahdjukaar/amendments/client/ClientResourceGenerator.generateHangingSignAssets, net.mehvahdjukaar.amendments.client.ClientResourceGenerator$$Lambda$47294+0x000002159a25ea18/1600728951.accept, net/mehvahdjukaar/moonlight/api/resources/pack/DynResourceGenerator.lambda$regenerateDynamicAssets$0.
- JFR execution samples for thread `pool-6-thread-4`: n=22; most frequent stack frames: java/lang/String.join, cpw/mods/niofs/union/UnionPath.toString, cpw/mods/niofs/union/UnionFileSystem.readAttributes, jdk/nio/zipfs/ZipFileSystem.getInode, java/util/stream/ReferencePipeline$2$1.accept.
- JFR execution samples for thread `pool-6-thread-5`: n=2; most frequent stack frames: net/minecraftforge/resource/DelegatingPackResources.m_214146_, net/minecraft/server/packs/resources/FallbackResourceManager.m_213713_, net/minecraft/server/packs/resources/MultiPackResourceManager.m_213713_, com/teamabnormals/blueprint/common/remolder/RemoldedResourceManager.m_213713_, net/mehvahdjukaar/moonlight/api/resources/textures/TextureImage.open.
- JFR thread allocation counters: 67.77 MiB/s aggregate over 722.67 s; highest threads: main 48623.93 MiB, modloading-worker-0 172.96 MiB, modloading-worker-0 51.64 MiB, Worker-ResourceReload-1 40.78 MiB, FancyMenu-WebUtils-ConnectivityCheck-1 19.48 MiB.
  Sampled object classes: [B (22082), java/util/concurrent/ConcurrentHashMap$ValueIterator (5106), java/lang/reflect/Field (5035), java/lang/String (4094), [Ljava/lang/Object; (3704); sampled allocation sites: com/electronwill/nightconfig/core/file/FileWatcher$WatcherThread.run (4985), net/raphimc/immediatelyfast/feature/core/BatchableBufferSource.m_109912_ (3274), net/minecraft/server/packs/FilePackResources.m_8031_ (2867), net/raphimc/immediatelyfast/feature/core/BatchableBufferSource.getBufferBuilder (2549), net/minecraft/resources/ResourceLocation.m_135828_ (2237). Counts are JFR samples, not exact object counts.
