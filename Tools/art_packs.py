"""The Garden and Master packs: sixteen different pictures (art_scenes.py), one subject each.

Earlier versions used parametric patterns (quilts, spirals, targets, rosettes, mazes) and repeated
them across levels with new colours; every level now has its own design, and none repeats a main
or Challenge picture (ladybird, koi, peacock, market, sunflower, rings, weave, labyrinth, rose window).
"""
from art_scenes import SCENES

# key, title, subtitle, scene, seed (the seed drives the level builder, not the picture)
GARDEN = [
    ("gardenBalloon", "Hot-Air Balloon", "Garden · drifting over the fields", "balloon", 41),
    ("gardenLighthouse", "Lighthouse", "Garden · a beacon on the rocks", "lighthouse", 42),
    ("gardenToadstools", "Toadstools", "Garden · red caps in the woods", "toadstools", 43),
    ("gardenTulips", "Tulip Bed", "Garden · seven tulips in a row", "tulips", 44),
    ("gardenSailboat", "Evening Sail", "Garden · a sailboat at sunset", "sailboat", 45),
    ("gardenBees", "Honeycomb", "Garden · bees at work on the comb", "honeycomb", 46),
    ("gardenOwl", "Owl", "Garden · wide awake on a branch", "owl", 47),
    ("gardenDesert", "Desert Bloom", "Garden · cacti under a red mesa", "desert", 48),
]
MASTER = [
    ("masterTiger", "Tiger", "Master · every stripe its own island", "tiger", 71),
    ("masterGiraffe", "Giraffe", "Master · a coat of a hundred patches", "giraffe", 52),
    ("masterAutumn", "Autumn Tree", "Master · hundreds of loose leaves", "autumn", 53),
    ("masterCastle", "Castle", "Master · brick by brick", "castle", 54),
    ("masterViaduct", "Viaduct", "Master · a steam train over the arches", "viaduct", 55),
    ("masterSkyline", "City at Dusk", "Master · lit windows, one by one", "skyline", 56),
    ("masterChameleon", "Chameleon", "Master · bands, spots and a curled tail", "chameleon", 57),
    ("masterOctopus", "Octopus", "Master · eight arms, rows of suckers", "octopus", 58),
]


# Master levels built with the bar-checked search (generate_levels.build_master_to_bar): on these
# pictures the plain search either made the level too hard even for a thinking player (Viaduct) or
# left careless play winning too often on Classic (Tiger, Giraffe, City at Dusk).
BAR_CHECKED = {"masterTiger", "masterGiraffe", "masterViaduct", "masterSkyline"}


def master_kind(key):
    return "master_bar" if key in BAR_CHECKED else "master"


def art_for(scene, seed=None):
    return SCENES[scene]()


# ---------------------------------------------------------------------------
# The collection packs: themed packs of 8 (seven added on 27 Sep, seven Literature packs on 2 Oct), each
# running from gentle to fiendish.
# Pictures are drawn in art_wild.py, art_gallery.py, art_worldart.py, art_ancient.py, art_voyages.py,
# art_modern.py and art_cosmos.py. Artworks are public-domain paintings and objects (all made before
# 1930 by artists who died before 1956); history scenes are original compositions.
#
# tier: "gentle" (the Garden builder), "challenge" (re-dealt tunnels, checked against the Challenge
# bar) or "master" (re-dealt tunnels, checked against the Master bar).
# ---------------------------------------------------------------------------
import importlib

# pack id, Home title, picture module, [(key, title, subtitle, scene, seed, tier), ...]
COLLECTION = [
    ("wild", "WILD WONDERS", "art_wild", [
        ("wildIceberg", "Iceberg", "Wild Wonders · Antarctic waters", "iceberg", 1104, "gentle"),
        ("wildAurora", "Northern Lights", "Wild Wonders · Arctic skies", "aurora", 1101, "gentle"),
        ("wildRainforest", "Rainforest", "Wild Wonders · Amazon canopy", "rainforest", 1106, "challenge"),
        ("wildBamboo", "Bamboo Grove", "Wild Wonders · a giant panda in Sichuan", "bamboo", 1108, "master"),
        ("wildCanyon", "Grand Canyon", "Wild Wonders · Arizona's layered rock", "canyon", 1102, "gentle"),
        ("wildFalls", "Victoria Falls", "Wild Wonders · Zambia & Zimbabwe", "falls", 1103, "gentle"),
        ("wildVolcano", "Volcano", "Wild Wonders · fire at dusk", "volcano", 1105, "challenge"),
        ("wildReef", "Coral Reef", "Wild Wonders · the Great Barrier Reef", "reef", 1107, "master"),
    ]),
    ("gallery", "GALLERY", "art_gallery", [
        ("gallerySunrise", "Impression, Sunrise", "Gallery · Claude Monet, 1872", "sunrise", 1201, "gentle"),
        ("galleryPearl", "Girl with a Pearl Earring", "Gallery · Johannes Vermeer, c. 1665", "pearl", 1203, "gentle"),
        ("galleryMonaLisa", "Mona Lisa", "Gallery · Leonardo da Vinci, c. 1503", "monalisa", 1204, "gentle"),
        ("galleryLilyPond", "The Water Lily Pond", "Gallery · Claude Monet, 1899", "lilypond", 1202, "gentle"),
        ("galleryStarryNight", "The Starry Night", "Gallery · Vincent van Gogh, 1889", "starrynight", 1206, "challenge"),
        ("galleryGrandeJatte", "La Grande Jatte", "Gallery · Georges Seurat, 1884–86", "grandejatte", 1207, "master"),
        ("galleryKiss", "The Kiss", "Gallery · Gustav Klimt, 1907–08", "kiss", 1208, "master"),
        ("galleryScream", "The Scream", "Gallery · Edvard Munch, 1893", "scream", 1205, "challenge"),
    ]),
    ("worldart", "WORLD ART", "art_worldart", [
        ("worldMingVase", "Ming Vase", "World Art · Ming dynasty, 15th century", "mingvase", 1303, "gentle"),
        ("worldCircles", "Several Circles", "World Art · Kandinsky, 1926", "circles", 1304, "gentle"),
        ("worldGreatWave", "The Great Wave", "World Art · Hokusai, c. 1831", "greatwave", 1301, "gentle"),
        ("worldShower", "Sudden Shower", "World Art · Hiroshige, 1857", "shower", 1302, "gentle"),
        ("worldAlhambra", "Alhambra Tiles", "World Art · Granada, 14th century", "alhambra", 1307, "master"),
        ("worldSunStone", "Sun Stone", "World Art · Aztec, c. 1502–21", "sunstone", 1305, "challenge"),
        ("worldRavenna", "Starry Vault", "World Art · Ravenna, c. 425", "ravenna", 1306, "challenge"),
        ("worldMondrian", "Composition", "World Art · Mondrian, 1921", "mondrian", 1308, "master"),
    ]),
    ("ancient", "ANCIENT WORLD", "art_ancient", [
        ("ancientStonehenge", "Stonehenge", "Ancient World · midsummer, c. 2500 BC", "stonehenge", 1403, "gentle"),
        ("ancientLascaux", "Lascaux Cave", "Ancient World · c. 17,000 BC", "lascaux", 1401, "gentle"),
        ("ancientOlympia", "First Olympics", "Ancient World · Olympia, 776 BC", "olympia", 1405, "challenge"),
        ("ancientMask", "Golden Mask", "Ancient World · Tutankhamun, c. 1323 BC", "goldenmask", 1404, "challenge"),
        ("ancientTerracotta", "Terracotta Army", "Ancient World · Xi'an, c. 210 BC", "terracotta", 1407, "master"),
        ("ancientGreatWall", "The Great Wall", "Ancient World · from 221 BC", "greatwall", 1406, "challenge"),
        ("ancientPyramids", "The Great Pyramid", "Ancient World · Giza, c. 2560 BC", "pyramids", 1402, "gentle"),
        ("ancientColosseum", "The Colosseum", "Ancient World · Rome, AD 80", "colosseum", 1408, "master"),
    ]),
    ("voyages", "VOYAGES", "art_voyages", [
        ("voyageTreasureShip", "Treasure Ship", "Voyages · Zheng He, 1405", "treasureship", 1504, "gentle"),
        ("voyageSilkRoad", "Silk Road", "Voyages · a caravan at dusk", "silkroad", 1503, "gentle"),
        ("voyageWayfinders", "Wayfinders", "Voyages · Pacific, c. 1000", "wayfinders", 1501, "gentle"),
        ("voyageLongship", "Viking Longship", "Voyages · North Atlantic, c. 1000", "longship", 1502, "gentle"),
        ("voyagePress", "Printing Press", "Voyages · Mainz, c. 1450", "printingpress", 1505, "challenge"),
        ("voyageGalileo", "Galileo's Moons", "Voyages · Padua, 1610", "galileo", 1506, "challenge"),
        ("voyageGalapagos", "Galápagos", "Voyages · Darwin, 1835", "galapagos", 1507, "master"),
        ("voyageSouthPole", "South Pole", "Voyages · 1911", "southpole", 1508, "master"),
    ]),
    ("modern", "MODERN MOMENTS", "art_modern", [
        ("modernLiberty", "Liberty", "Modern Moments · New York Harbor, 1886", "liberty", 1602, "gentle"),
        ("modernFirstFlight", "First Flight", "Modern Moments · Kitty Hawk, 1903", "firstflight", 1601, "gentle"),
        ("modernEiffel", "Eiffel Tower", "Modern Moments · Paris World's Fair, 1889", "eiffel", 1603, "gentle"),
        ("modernGoldenGate", "Golden Gate", "Modern Moments · San Francisco, 1937", "goldengate", 1604, "gentle"),
        ("modernSputnik", "Sputnik", "Modern Moments · the first satellite, 1957", "sputnik", 1606, "challenge"),
        ("modernBerlinWall", "Berlin Wall", "Modern Moments · November 1989", "berlinwall", 1608, "master"),
        ("modernEverest", "Everest Summit", "Modern Moments · 1953", "everest", 1605, "challenge"),
        ("modernMoon", "Moon Landing", "Modern Moments · Sea of Tranquility, 1969", "moonlanding", 1607, "master"),
    ]),
    ("cosmos", "SKY & SCIENCE", "art_cosmos", [
        ("cosmosHalley", "Halley's Comet", "Sky & Science · 1910", "halley", 1703, "gentle"),
        ("cosmosPrism", "Newton's Prism", "Sky & Science · 1666", "prism", 1704, "gentle"),
        ("cosmosSaturn", "Saturn", "Sky & Science · the ringed planet", "saturn", 1702, "gentle"),
        ("cosmosEclipse", "Total Eclipse", "Sky & Science · totality", "eclipse", 1701, "gentle"),
        ("cosmosGalaxy", "Spiral Galaxy", "Sky & Science · an island universe", "galaxy", 1706, "challenge"),
        ("cosmosPeriodic", "Periodic Table", "Sky & Science · Mendeleev, 1869", "periodic", 1708, "master"),
        ("cosmosKite", "Franklin's Kite", "Sky & Science · 1752", "kite", 1705, "challenge"),
        ("cosmosHelix", "Double Helix", "Sky & Science · DNA, 1953", "helix", 1707, "master"),
    ]),
    ("epics", "EPICS & LEGENDS", "art_myths", [
        ("epicsSirens", "The Sirens", "Epics & Legends · Homer's Odyssey", "sirens", 1801, "gentle"),
        ("epicsMonkeyKing", "The Monkey King", "Epics & Legends · Journey to the West", "monkeyking", 1805, "challenge"),
        ("epicsTrojanHorse", "The Trojan Horse", "Epics & Legends · Virgil's Aeneid", "trojanhorse", 1802, "gentle"),
        ("epicsSwordStone", "The Sword in the Stone", "Epics & Legends · Malory's Le Morte d'Arthur", "swordstone", 1803, "gentle"),
        ("epicsCelestialRose", "The Celestial Rose", "Epics & Legends · Dante's Paradiso", "celestialrose", 1804, "gentle"),
        ("epicsAliBaba", "Ali Baba's Cave", "Epics & Legends · One Thousand and One Nights", "alibaba", 1806, "challenge"),
        ("epicsDragonHoard", "The Dragon's Hoard", "Epics & Legends · Beowulf", "dragonhoard", 1807, "master"),
        ("epicsGenji", "Moon over the Palace", "Epics & Legends · The Tale of Genji", "genji", 1808, "master"),
    ]),
    ("tales", "FAIRY TALES & FABLES", "art_tales", [
        ("talesTortoiseHare", "The Tortoise and the Hare", "Fairy Tales · Aesop's Fables", "tortoisehare", 1903, "gentle"),
        ("talesBeanstalk", "Jack and the Beanstalk", "Fairy Tales · English folk tale", "beanstalk", 1902, "gentle"),
        ("talesRapunzel", "Rapunzel", "Fairy Tales · Brothers Grimm", "rapunzel", 1904, "gentle"),
        ("talesSnowQueen", "The Snow Queen", "Fairy Tales · Hans Christian Andersen", "snowqueen", 1905, "challenge"),
        ("talesRedRidingHood", "Little Red Riding Hood", "Fairy Tales · Brothers Grimm", "redridinghood", 1901, "gentle"),
        ("talesPrincessPea", "The Princess and the Pea", "Fairy Tales · Hans Christian Andersen", "princesspea", 1908, "master"),
        ("talesCinderella", "Cinderella's Midnight", "Fairy Tales · Charles Perrault", "cinderella", 1906, "challenge"),
        ("talesGingerbread", "The Gingerbread House", "Fairy Tales · Brothers Grimm", "gingerbread", 1907, "master"),
    ]),
    ("childrens", "CHILDREN'S CLASSICS", "art_childrens", [
        ("kidsYellowBrick", "The Yellow Brick Road", "Children's Classics · L. Frank Baum, 1900", "yellowbrick", 2001, "gentle"),
        ("kidsRiverbank", "Messing About in Boats", "Children's Classics · Kenneth Grahame, 1908", "riverbank", 2002, "gentle"),
        ("kidsSecretGarden", "The Secret Garden", "Children's Classics · Frances Hodgson Burnett, 1911", "secretgarden", 2004, "gentle"),
        ("kidsRailway", "The Railway Children", "Children's Classics · E. Nesbit, 1906", "railwaychildren", 2003, "gentle"),
        ("kidsCouncilRock", "The Council Rock", "Children's Classics · Rudyard Kipling, 1894", "wolfpack", 2006, "challenge"),
        ("kidsPinocchio", "Inside the Dogfish", "Children's Classics · Carlo Collodi, 1883", "pinocchio", 2008, "master"),
        ("kidsTeaParty", "The Mad Tea-Party", "Children's Classics · Lewis Carroll, 1865", "teaparty", 2005, "challenge"),
        ("kidsLookingGlass", "Through the Looking-Glass", "Children's Classics · Lewis Carroll, 1871", "lookingglass", 2007, "master"),
    ]),
    ("stage", "SHAKESPEARE", "art_stage", [
        ("stageWitches", "The Three Witches", "Shakespeare · Macbeth", "witches", 2103, "gentle"),
        ("stageBalcony", "The Balcony", "Shakespeare · Romeo and Juliet", "balcony", 2101, "gentle"),
        ("stageTempest", "The Shipwreck", "Shakespeare · The Tempest", "tempest", 2104, "gentle"),
        ("stageYorick", "Alas, Poor Yorick", "Shakespeare · Hamlet", "yorick", 2102, "gentle"),
        ("stageFairyWood", "The Fairy Wood", "Shakespeare · A Midsummer Night's Dream", "fairywood", 2105, "challenge"),
        ("stageCleopatra", "Cleopatra's Barge", "Shakespeare · Antony and Cleopatra", "cleopatra", 2106, "challenge"),
        ("stageGlobe", "The Globe", "Shakespeare · the Globe Theatre, 1599", "globe", 2107, "master"),
        ("stageCaskets", "The Three Caskets", "Shakespeare · The Merchant of Venice", "caskets", 2108, "master"),
    ]),
    ("adventure", "ADVENTURE CLASSICS", "art_adventure", [
        ("advWindmills", "Tilting at Windmills", "Adventure · Miguel de Cervantes, 1605", "windmills", 2202, "gentle"),
        ("advLilliput", "Gulliver in Lilliput", "Adventure · Jonathan Swift, 1726", "lilliput", 2204, "gentle"),
        ("advNautilus", "The Nautilus", "Adventure · Jules Verne, 1870", "nautilus", 2208, "master"),
        ("advUndergroundSea", "The Underground Sea", "Adventure · Jules Verne, 1864", "undergroundsea", 2206, "challenge"),
        ("advRaft", "The Raft", "Adventure · Mark Twain, 1884", "raft", 2203, "gentle"),
        ("advWhiteWhale", "The White Whale", "Adventure · Herman Melville, 1851", "whitewhale", 2205, "challenge"),
        ("advFootprint", "The Footprint", "Adventure · Daniel Defoe, 1719", "footprint", 2209, "gentle"),
        ("advTreasureMap", "The Treasure Map", "Adventure · Robert Louis Stevenson, 1883", "treasuremap", 2207, "master"),
    ]),
    ("gothic", "GOTHIC & MYSTERY", "art_gothic", [
        ("gothicRaven", "The Raven", "Gothic & Mystery · Edgar Allan Poe, 1845", "raven", 2301, "gentle"),
        ("gothicHound", "The Hound on the Moor", "Gothic & Mystery · Arthur Conan Doyle, 1902", "hound", 2303, "gentle"),
        ("gothicNotreDame", "The Bells of Notre-Dame", "Gothic & Mystery · Victor Hugo, 1831", "notredame", 2304, "gentle"),
        ("gothicArctic", "Across the Ice", "Gothic & Mystery · Mary Shelley, 1818", "arctic", 2306, "challenge"),
        ("gothicHorseman", "The Headless Horseman", "Gothic & Mystery · Washington Irving, 1820", "horseman", 2302, "gentle"),
        ("gothicDracula", "Castle Dracula", "Gothic & Mystery · Bram Stoker, 1897", "dracula", 2305, "challenge"),
        ("gothicChandelier", "The Great Chandelier", "Gothic & Mystery · Gaston Leroux, 1910", "chandelier", 2308, "master"),
        ("gothicTripods", "The Martian Tripods", "Gothic & Mystery · H. G. Wells, 1898", "tripods", 2307, "master"),
    ]),
    ("novels", "GREAT NOVELS", "art_novels", [
        ("novelChristmas", "Christmas Morning", "Great Novels · Charles Dickens, 1843", "christmascarol", 2402, "gentle"),
        ("novelWuthering", "Wuthering Heights", "Great Novels · Emily Brontë, 1847", "wuthering", 2403, "gentle"),
        ("novelComet", "The Comet of 1812", "Great Novels · Leo Tolstoy, 1869", "comet1812", 2404, "gentle"),
        ("novelHavisham", "Miss Havisham's Room", "Great Novels · Charles Dickens, 1861", "havisham", 2405, "challenge"),
        ("novelGreenLight", "The Green Light", "Great Novels · F. Scott Fitzgerald, 1925", "greenlight", 2401, "gentle"),
        ("novelCandlesticks", "The Silver Candlesticks", "Great Novels · Victor Hugo, 1862", "candlesticks", 2406, "challenge"),
        ("novelNetherfield", "The Netherfield Ball", "Great Novels · Jane Austen, 1813", "netherfield", 2407, "master"),
        ("novelWorkhouse", "I Want Some More", "Great Novels · Charles Dickens, 1838", "workhouse", 2408, "master"),
    ]),
    ("naturalist", "NATURAL HISTORY", "art_naturalist", [
        ("natFlamingo", "Audubon's Flamingo", "Natural History · after Audubon, The Birds of America, 1838", "flamingo", 2501, "gentle"),
        ("natMetamorphosis", "Merian's Butterflies", "Natural History · after Merian, Insects of Surinam, 1705", "metamorphosis", 2503, "gentle"),
        ("natHummingbirds", "Gould's Hummingbirds", "Natural History · after Gould's hummingbird plates, 1849–1861", "hummingbirds", 2504, "gentle"),
        ("natRose", "Redouté's Rose", "Natural History · after Redouté, Les Roses, 1817–1824", "rose", 2502, "gentle"),
        ("natJellyfish", "Haeckel's Jellyfish", "Natural History · after Haeckel, Art Forms in Nature, 1904", "jellyfish", 2505, "challenge"),
        ("natShells", "Seba's Shells", "Natural History · after Seba's cabinet of curiosities, 1734–1765", "shells", 2506, "challenge"),
        ("natBeetles", "The Beetle Drawer", "Natural History · a collector's cabinet", "beetles", 2508, "master"),
        ("natRadiolarians", "Haeckel's Radiolarians", "Natural History · microscopic skeletons, after Haeckel, 1904", "radiolarians", 2507, "master"),
    ]),
    ("crafts", "WORLD CRAFT", "art_crafts", [
        ("craftPysanky", "Pysanky Eggs", "World Craft · Ukrainian painted eggs", "pysanky", 2603, "gentle"),
        ("craftTalavera", "Talavera Plate", "World Craft · Puebla, Mexico", "talavera", 2601, "gentle"),
        ("craftPaperCut", "Wycinanki", "World Craft · a Polish paper cut", "papercut", 2602, "gentle"),
        ("craftTartan", "Tartan", "World Craft · Scotland, a woven plaid", "tartan", 2606, "challenge"),
        ("craftDelft", "Delft Tiles", "World Craft · the Netherlands, blue and white", "delft", 2604, "gentle"),
        ("craftCarpet", "Persian Carpet", "World Craft · Iran, a medallion carpet", "carpet", 2608, "master"),
        ("craftAsanoha", "Asanoha Kimono", "World Craft · Japan, the hemp-leaf pattern", "asanoha", 2605, "challenge"),
        ("craftQuilt", "Patchwork Quilt", "World Craft · American star blocks", "quilt", 2607, "master"),
    ]),
    ("geometry", "GEOMETRY & ILLUSIONS", "art_geometry", [
        ("geoMandelbrot", "Mandelbrot Set", "Geometry & Illusions · a fractal, 1980", "mandelbrot", 2713, "gentle"),
        ("geoTriangle", "Impossible Triangle", "Geometry & Illusions · the impossible tribar", "triangle", 2721, "gentle"),
        ("geoSpiral", "Golden Spiral", "Geometry & Illusions · Fibonacci's squares", "spiral", 2702, "gentle"),
        ("geoSierpinski", "Sierpiński Triangle", "Geometry & Illusions · a fractal, 1915", "sierpinski", 2704, "challenge"),
        ("geoCafeWall", "Café Wall", "Geometry & Illusions · do the rows slope?", "cafewall", 2706, "challenge"),
        ("geoHilbert", "Hilbert Curve", "Geometry & Illusions · a space-filling curve, 1891", "hilbert", 2705, "challenge"),
        ("geoCelticKnot", "Celtic Knot", "Geometry & Illusions · over-and-under interlace", "knot", 2707, "master"),
        ("geoGirih", "Girih Star", "Geometry & Illusions · ten-pointed Islamic star pattern", "girih", 2708, "master"),
    ]),
    ("space", "PROBES & TELESCOPES", "art_space", [
        ("spaceEarthrise", "Earthrise", "Probes & Telescopes · Apollo 8, 1968", "earthrise", 2801, "gentle"),
        ("spacePlutoHeart", "Pluto's Heart", "Probes & Telescopes · New Horizons, 2015", "plutoheart", 2802, "gentle"),
        ("spaceMarsSunset", "Blue Sunset on Mars", "Probes & Telescopes · a rover's view", "marssunset", 2804, "gentle"),
        ("spacePillars", "Pillars of Creation", "Probes & Telescopes · Hubble, 1995", "pillars", 2805, "challenge"),
        ("spaceRover", "Rover on Mars", "Probes & Telescopes · six wheels on red rock", "rover", 2806, "challenge"),
        ("spaceRedSpot", "Jupiter's Great Red Spot", "Probes & Telescopes · Voyager and Juno", "redspot", 2803, "gentle"),
        ("spaceCliffs", "Cosmic Cliffs", "Probes & Telescopes · Webb, 2022", "cliffs", 2807, "master"),
        ("spaceDeepField", "Hubble Deep Field", "Probes & Telescopes · thousands of galaxies, 1995", "deepfield", 2808, "master"),
    ]),
    ("inventions", "INVENTIONS & FIRSTS", "art_inventions", [
        ("invLightBulb", "The Light Bulb", "Inventions & Firsts · a glowing filament, 1879", "lightbulb", 2902, "gentle"),
        ("invFlyingMachine", "Da Vinci's Flying Machine", "Inventions & Firsts · Leonardo's notebooks, c. 1488", "flyingmachine", 2904, "gentle"),
        ("invTelephone", "The Telephone", "Inventions & Firsts · a candlestick telephone", "telephone", 2903, "gentle"),
        ("invPennyFarthing", "Penny-Farthing", "Inventions & Firsts · the high-wheel bicycle, 1870s", "pennyfarthing", 2901, "gentle"),
        ("invLoom", "Jacquard Loom", "Inventions & Firsts · punched cards weave a pattern, 1804", "loom", 2907, "master"),
        ("invDifferenceEngine", "Difference Engine", "Inventions & Firsts · Babbage's calculating machine, 1822", "diffengine", 2908, "master"),
        ("invRocket", "Stephenson's Rocket", "Inventions & Firsts · a steam locomotive, 1829", "rocket", 2905, "challenge"),
        ("invFirstPhoto", "The First Photograph", "Inventions & Firsts · a camera at the window, 1826", "firstphoto", 2906, "challenge"),
    ]),
    ("halloween", "HALLOWEEN", "art_halloween", [
        ("halloBlackCat", "Black Cat on the Fence", "Halloween · under the harvest moon", "blackcat", 3002, "gentle"),
        ("halloTrickOrTreat", "Trick-or-Treat Street", "Halloween · costumes under the streetlamp", "trickortreat", 3008, "master"),
        ("halloJackOLantern", "Jack-o'-Lantern", "Halloween · a carved pumpkin glows", "jackolantern", 3001, "gentle"),
        ("halloGhosts", "Friendly Ghosts", "Halloween · a parade at dusk", "ghosts", 3004, "gentle"),
        ("halloScarecrow", "Scarecrow", "Halloween · in the cornfield", "scarecrow", 3003, "gentle"),
        ("halloHauntedHouse", "Haunted House", "Halloween · on the hill", "hauntedhouse", 3005, "challenge"),
        ("halloPumpkinPatch", "Pumpkin Patch", "Halloween · harvest time", "pumpkinpatch", 3006, "challenge"),
        ("halloSpiderWeb", "Spider's Web", "Halloween · dew and fallen leaves", "spiderweb", 3007, "master"),
    ]),
    ("winter", "WINTER", "art_winter", [
        ("winterCocoa", "Mittens & Cocoa", "Winter · warming up", "cocoa", 3104, "gentle"),
        ("winterSledding", "Sledding Hill", "Winter · the first snow day", "sledding", 3103, "gentle"),
        ("winterSnowman", "Snowman", "Winter · a knit hat and a scarf", "snowman", 3101, "gentle"),
        ("winterCardinal", "Cardinal in the Snow", "Winter · a red bird on a snowy bough", "cardinal", 3102, "gentle"),
        ("winterSnowflake", "Bentley's Snowflake", "Winter · after Wilson Bentley's snow crystals", "snowflake", 3105, "challenge"),
        ("winterSkating", "The Skating Pond", "Winter · after Currier & Ives, 1862", "skating", 3106, "challenge"),
        ("winterSnowGlobe", "Snow Globe", "Winter · a village under glass", "snowglobe", 3107, "master"),
        ("winterFrostWindow", "Frosted Window", "Winter · candlelight behind the frost", "frostwindow", 3108, "master"),
    ]),
]


def collection_art(module, scene):
    return importlib.import_module(module).SCENES[scene]()


def collection_jobs():
    """Level-builder jobs for the collection packs, in catalogue order."""
    jobs = []
    for pack, _, module, levels in COLLECTION:
        for key, title, sub, scene, seed, tier in levels:
            s = seed * 101 + 7 if tier == "gentle" else seed * 131 + 11
            jobs.append(("pack", tier, pack, key, title, sub, s, collection_art(module, scene)))
    return jobs
