# Extractos oficiales FNF v0.8.6

- Release: https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6
- Installing mods: https://github.com/FunkinCrew/Funkin/blob/v0.8.6/docs/INSTALLING_MODS.md

## docs/INSTALLING_MODS.md
5:1. Start the game at least once. This will create a `mods` folder if it doesn't already exist, alongside the executable.
6:2. Extract the mod you downloaded from its ZIP file, and place the mod folder into the game's `mods` folder.
10:1. Start the game at least once. This will create a `mods` folder if it doesn't already exist, alongside the executable.
11:2. Extract the mod you downloaded from its ZIP file, and place the mod folder into the game's `mods` folder.
15:1. Start the game at least once. This will create a `mods` folder if it doesn't already exist in the game's system files.
17:3. Navigate to `Contents/Resources/mods`.
18:4. Extract the mod you downloaded from its ZIP file, and place the mod folder into the game's `mods` folder.
22:1. Start the game at least once. This will create a `mods` folder deep in your system files.
24:3. Locate the `/sdcard/Android/obb/me.funkin.fnf/mods` folder.
25:4. Extract the mod you downloaded from its ZIP file, and place the mod folder into the game's `mods` folder.
29:1. Start the game at least once. This will create a `mods` folder in your system files.
30:2. Open the Files app, and navigate to `On My iPhone` -> `Friday Night Funkin` -> `mods`.
31:3. Extract the mod you downloaded from its ZIP file, and place the mod folder into the game's `mods` folder.

## source/funkin/data/song/SongRegistry.hx
22:   * The current version string for the stage data format.
44:    super('SONG', 'songs', SONG_METADATA_VERSION_RULE);
84:    var entryIdList:Array<String> = DataAssets.listDataFilesInPath('songs/', '-metadata.json').map(function(songDataPath:String):String
214:  public function parseEntryMetadataWithMigration(id:String, variation:String, version:thx.semver.Version):Null<SongMetadata>
218:    // If a version rule is not specified, do not check against it.
219:    if (SONG_METADATA_VERSION_RULE == null || VersionUtil.validateVersion(version, SONG_METADATA_VERSION_RULE))
223:    else if (VersionUtil.validateVersion(version, '2.1.x'))
227:    else if (VersionUtil.validateVersion(version, '2.0.x'))
233:      throw '[${registryId}] Metadata entry ${id}:${variation} does not support migration to version ${SONG_METADATA_VERSION_RULE}.';
237:  public function parseEntryMetadataRawWithMigration(contents:String, ?fileName:String = 'raw', version:thx.semver.Version,
240:    // If a version rule is not specified, do not check against it.
241:    if (SONG_METADATA_VERSION_RULE == null || VersionUtil.validateVersion(version, SONG_METADATA_VERSION_RULE))
245:    else if (VersionUtil.validateVersion(version, '2.1.x'))
249:    else if (VersionUtil.validateVersion(version, '2.0.x'))
255:      throw '[${registryId}] Metadata entry "${fileName}" does not support migration to version ${SONG_METADATA_VERSION_RULE}.';
368:  public function parseMusicDataWithMigration(id:String, ?variation:String, version:thx.semver.Version):Null<SongMusicData>
372:    // If a version rule is not specified, do not check against it.
373:    if (SONG_MUSIC_DATA_VERSION_RULE == null || VersionUtil.validateVersion(version, SONG_MUSIC_DATA_VERSION_RULE))
379:      throw '[${registryId}] Chart entry ${id}:${variation} does not support migration to version ${SONG_MUSIC_DATA_VERSION_RULE}.';
383:  public function parseMusicDataRawWithMigration(contents:String, ?fileName:String = 'raw', version:thx.semver.Version):Null<SongMusicData>
385:    // If a version rule is not specified, do not check against it.
386:    if (SONG_MUSIC_DATA_VERSION_RULE == null || VersionUtil.validateVersion(version, SONG_MUSIC_DATA_VERSION_RULE))
392:      throw '[${registryId}] Chart entry "$fileName" does not support migration to version ${SONG_MUSIC_DATA_VERSION_RULE}.';
435:  public function parseEntryChartDataWithMigration(id:String, ?variation:String, version:thx.semver.Version):Null<SongChartData>
439:    // If a version rule is not specified, do not check against it.
440:    if (SONG_CHART_DATA_VERSION_RULE == null || VersionUtil.validateVersion(version, SONG_CHART_DATA_VERSION_RULE))
446:      throw '[${registryId}] Chart entry ${id}:${variation} does not support migration to version ${SONG_CHART_DATA_VERSION_RULE}.';
450:  public function parseEntryChartDataRawWithMigration(contents:String, ?fileName:String = 'raw', version:thx.semver.Version,
453:    // If a version rule is not specified, do not check against it.
454:    if (SONG_CHART_DATA_VERSION_RULE == null || VersionUtil.validateVersion(version, SONG_CHART_DATA_VERSION_RULE))
460:      throw '[${registryId}] Chart entry "${fileName}" does not support migration to version ${SONG_CHART_DATA_VERSION_RULE}.';

## source/funkin/data/song/SongData.hx
22:   * A semantic versioning string for the song data format.
26:  public var version:Version;
64:    this.version = SongRegistry.SONG_METADATA_VERSION;
76:    this.playData.characters = new SongCharacterData('bf', 'gf', 'dad');
92:    result.version = this.version;
112:    // Update generatedBy and version before writing.
137:    this.version = SongRegistry.SONG_METADATA_VERSION;
261:   * The offset, in milliseconds, to apply to the songs vocals, relative to each alternate instrumental.
343:   * A semantic versioning string for the song data format.
347:  public var version:Version;
372:    this.version = SongRegistry.SONG_CHART_DATA_VERSION;
386:    this.version = SongRegistry.SONG_MUSIC_DATA_VERSION;
393:    result.version = this.version;
426:   * The characters used by this song.
428:  public var characters:SongCharacterData;
495:    result.characters = this.characters.clone();
516: * Information about the characters used in this variation of the song.
517: * Create a new variation if you want to change the characters.
572:  public var version:Version;
588:    this.version = SongRegistry.SONG_CHART_DATA_VERSION;
632:    // Update generatedBy and version before writing.
642:    this.version = SongRegistry.SONG_CHART_DATA_VERSION;
657:    result.version = this.version;

## source/funkin/data/character/CharacterData.hx
27:   * The current version string for the stage data format.
36:   * The current version rule check for the stage data format.
47:   * If you want to force stages to be reloaded, you can just call this function again.
51:    // Clear any stages that are cached if there were any.
58:    var charIdList:Array<String> = DataAssets.listDataFilesInPath('characters/');
63:    log('Fetching data for ${unscriptedCharIds.length} characters...');
91:      log('Instantiating ${scriptedCharClassNames1.length} (Sparrow) scripted characters...');
111:      log('Instantiating ${scriptedCharClassNames2.length} (Packer) scripted characters...');
131:      log('Instantiating ${scriptedCharClassNames3.length} (Multi-Sparrow) scripted characters...');
151:      log('Instantiating ${scriptedCharClassNames4.length} (Animate Atlas) scripted characters...');
171:      log('Instantiating ${scriptedCharClassNames5.length} (Multi-Animate Atlas) scripted characters...');
202:      log('Instantiating ${scriptedCharClassNames.length} (Base) scripted characters...');
219:    log(' INFO '.info() + 'Successfully loaded ${characterCache.size()} stages.');
232:      // Gracefully handle songs that don't use this character,
416:    var charFilePath:String = Paths.json('characters/${charPath}');
430:    // handle migration here by checking the `version` value.
492:    if (input.version == null)
494:      trace('WARN: No semantic version specified for character data file "$id", assuming ${CHARACTER_DATA_VERSION}');
495:      input.version = CHARACTER_DATA_VERSION;
498:    if (!VersionUtil.validateVersionStr(input.version, CHARACTER_DATA_VERSION_RULE))
500:      trace('ERROR: Could not load character data for "$id": bad version (got ${input.version}, expected ${CHARACTER_DATA_VERSION_RULE})');
515:    if (input.assetPath == null)
517:      trace('ERROR: Could not load character data for "$id": missing assetPath');
715:   * The semantic version number of the character data JSON format.
717:  var version:String;
735:  var assetPath:String;
777:   * @default `1.0` on characters
806:   * Useful for characters that could also be played (Pico)
813:   * NOTE: This only applies to animate atlas characters.

## source/funkin/data/stage/StageData.hx
9:   * The semantic version number of the stage data JSON format.
13:  public var version:String;
17:  public var characters:StageDataCharacters;
21:  public var directory:Null<String>;
25:    this.version = StageRegistry.STAGE_DATA_VERSION;
26:    this.characters = makeDefaultCharacters();
58:    // Update generatedBy and version before writing.
67:    this.version = StageRegistry.STAGE_DATA_VERSION;
92:  var assetPath:String;
100:   * A number determining the stack order of the prop, relative to other props and the characters in the stage.
271:   * A number determining the stack order of the character, relative to props and other characters in the stage.

