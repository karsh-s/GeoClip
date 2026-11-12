"""
GeoTips-derived CLIP prompts, one short caption per visual cue.

WHY IT IS STRUCTURED THIS WAY
CLIP's text encoder truncates at 77 tokens. A single paragraph stuffing
every clue about a country would be silently cut off mid-sentence, so
each country instead gets several SHORT captions - one per cue family -
and their embeddings are averaged. That is standard prompt ensembling,
and it keeps every clue inside the token budget.

WHERE THIS IS USED
v7 classifies with a trained head on CLIP *image* features, so these
prompts do not affect its accuracy on their own. They are used for:
  1. the zero-shot baseline (what CLIP scores with no training)
  2. an optional text-anchor ensemble fused with the trained head,
     which the notebook measures rather than assumes

SOURCING
France and Ireland entries were read from geotips.net directly. The rest
come from general GeoGuessr meta knowledge in the same style; the site
keeps all countries on one large page that could not be paged through
in full. Treat individual details as good-but-unverified, and prefer
whatever the measured numbers say.

The countries outside Europe were added with the global model, from the
same general meta knowledge. make_cues.py embeds every cue and reports how
well each one separates its own country's imagery from everyone else's.
"""

# Cue families: bollard, lines, plates, poles, signs, arch, flora, misc
GEOTIPS = {
'Albania': {
  'arch': 'unfinished red brick and concrete houses with exposed rebar',
  'flora': 'dry mediterranean scrub on steep limestone hills',
  'signs': 'Albanian language signs, SH road numbers',
  'misc': 'many old Mercedes cars, older low-quality camera coverage',
  'lines': 'worn faded road markings on narrow patched tarmac'},
'Andorra': {
  'arch': 'stone and slate Pyrenean buildings with steep roofs',
  'flora': 'high alpine pine slopes and bare rock above the treeline',
  'signs': 'Catalan language signs, CG road numbers',
  'lines': 'white lines on winding mountain switchback roads',
  'misc': 'dense hillside apartment blocks in narrow valleys'},
'Austria': {
  'arch': 'tidy alpine houses with wide eaves and painted facades',
  'flora': 'steep spruce-covered alpine slopes and green meadows',
  'signs': 'German language signs, red and white striped markers',
  'bollard': 'grey and white reflector posts along mountain roads',
  'lines': 'crisp white centre lines on well maintained tarmac',
  'plates': 'white plates with a red and white stripe'},
'Belgium': {
  'arch': 'narrow brick row houses with varied rooflines',
  'flora': 'flat farmland with poplar rows and small woods',
  'signs': 'Dutch and French bilingual signs',
  'lines': 'concrete slab roads with visible joins and worn markings',
  'misc': 'motorways lit by long rows of orange street lights',
  'bollard': 'square white concrete bollards'},
'Bosnia and Herzegovina': {
  'arch': 'red tiled roofs, unfinished concrete, minarets and churches',
  'flora': 'steep green wooded hills and karst river valleys',
  'signs': 'Bosnian signs mixing Latin and Cyrillic script',
  'misc': 'older lower quality camera coverage, narrow patched roads',
  'lines': 'faded white lines, frequent guardrails on gorge roads'},
'Bulgaria': {
  'arch': 'communist era concrete blocks and red roofed village houses',
  'flora': 'rolling farmland, oak woods and bare limestone ridges',
  'signs': 'Cyrillic script road signs in Bulgarian',
  'bollard': 'black and white striped kerbstones and posts',
  'misc': 'older camera coverage, worn rural tarmac'},
'Croatia': {
  'arch': 'white limestone houses with orange terracotta roofs',
  'flora': 'karst scrub, cypress and pine near the Adriatic coast',
  'signs': 'Croatian language signs, D road numbers',
  'lines': 'white lines with stone walls lining narrow coastal roads',
  'plates': 'plates with a red and white chequered shield'},
'Cyprus': {
  'arch': 'flat roofed concrete houses with solar water tanks',
  'flora': 'dry yellow hills with olive and carob trees',
  'signs': 'Greek and English bilingual signs',
  'misc': 'traffic drives on the left, British style road furniture',
  'lines': 'double yellow lines at the kerb, wide chip seal roads'},
'Czech Republic': {
  'arch': 'pastel village houses with steep orange tiled roofs',
  'flora': 'rolling farmland with spruce plantations and hop fields',
  'signs': 'Czech language signs with hacek and acute accents',
  'bollard': 'white bollards with an orange reflector strip',
  'lines': 'white lines on grey tarmac, avenues of roadside trees',
  'misc': 'red and white striped guardrail ends'},
'Denmark': {
  'arch': 'red brick houses with white window frames, low and wide',
  'flora': 'very flat farmland, wind turbines and trimmed hedgerows',
  'signs': 'Danish language signs with the letters ae, oe and aa',
  'lines': 'white lines with wide separate cycle paths beside roads',
  'bollard': 'slim white posts with red reflectors'},
'Estonia': {
  'arch': 'wooden houses with steep roofs and Soviet era blocks',
  'flora': 'flat boreal pine and birch forest, bogs and reeds',
  'signs': 'Estonian language signs with umlauts and double vowels',
  'lines': 'white lines on narrow roads, long straight forest corridors',
  'misc': 'tall snow poles and reflector posts at the verge'},
'Finland': {
  'arch': 'wooden houses painted red or yellow among trees',
  'flora': 'dense boreal spruce and pine forest with lakes',
  'signs': 'Finnish and Swedish bilingual signs with double letters',
  'lines': 'white lines, wide gravel shoulders and reflector posts',
  'misc': 'frequent gravel roads through unbroken conifer forest'},
# --- read directly from geotips.net ---
'France': {
  'bollard': 'large white bollards, some with a red reflector band',
  'lines': 'dashed white shoulder lines and diamond shaped dashes',
  'poles': 'wooden utility poles marked with a small blue square sticker',
  'signs': 'blue and green arrow direction signs, street names using Rue',
  'arch': 'pale render houses with shutters and slate or tile roofs',
  'flora': 'plane trees lining roads, farmland and mixed woodland',
  'plates': 'white EU plates, older coverage with yellow rear plates'},
'Germany': {
  'arch': 'half timbered houses and tidy render homes with grey roofs',
  'flora': 'dense mixed farmland, beech woods and spruce plantations',
  'signs': 'German language signs, dense signage and clear white lettering',
  'bollard': 'white posts with black reflector tops',
  'lines': 'crisp white lines on smooth well maintained tarmac',
  'misc': 'red and white striped kerb posts, immaculate road surfaces'},
'Greece': {
  'arch': 'whitewashed flat roofed houses with concrete pillars',
  'flora': 'olive groves, dry scrub hills and cypress trees',
  'signs': 'Greek alphabet road signs, often with Latin transliteration',
  'lines': 'faded white lines on narrow winding roads with low walls',
  'misc': 'roadside shrines, unfinished concrete frames, dry stone walls'},
'Hungary': {
  'arch': 'single storey farmhouses gable end to the road',
  'flora': 'very flat plains, maize and sunflower fields, poplar rows',
  'signs': 'Hungarian language signs with double acute accents',
  'bollard': 'black and white striped kerbstones',
  'lines': 'white lines on flat straight roads with tree avenues'},
'Iceland': {
  'arch': 'corrugated metal clad houses, no trees around them',
  'flora': 'treeless volcanic terrain, moss, black lava and grass',
  'signs': 'Icelandic language signs with thorn and eth letters',
  'lines': 'yellow centre lines and yellow topped reflector posts',
  'misc': 'gravel roads, distant glaciers, wide empty basalt landscapes'},
# --- read directly from geotips.net ---
'Ireland': {
  'bollard': 'chunky green bollards, relatively rare',
  'lines': 'dashed yellow side lines and white centre markings',
  'plates': 'standard EU style plates',
  'poles': 'wooden utility poles throughout',
  'signs': 'English with Irish translations, green white and brown signs',
  'arch': 'boxy houses with the front door in the centre',
  'misc': 'traffic drives on the left, distances in kilometres'},
'Italy': {
  'arch': 'terracotta roofed houses with ochre and cream render',
  'flora': 'cypress trees, olive groves, vineyards and dry hills',
  'signs': 'Italian language signs, SP and SS road numbers',
  'bollard': 'white bollards with a black band near the top',
  'lines': 'white lines on narrow roads walled by stone or hedge',
  'misc': 'roadside shrines, tightly packed hilltop villages'},
'Latvia': {
  'arch': 'wooden farmhouses and Soviet era apartment blocks',
  'flora': 'flat pine and birch forest with wet meadows',
  'signs': 'Latvian language signs with macrons and cedillas',
  'lines': 'white lines on narrow roads, many unpaved gravel stretches',
  'bollard': 'black and white striped posts at the verge'},
'Liechtenstein': {
  'arch': 'immaculate alpine chalets with wide balconies',
  'flora': 'steep wooded alpine valley slopes above the Rhine',
  'signs': 'German language signs in Swiss style',
  'lines': 'flawless white lines on very clean narrow roads',
  'misc': 'dense tidy villages against sudden steep mountain walls'},
'Lithuania': {
  'arch': 'wooden village houses and low brick farm buildings',
  'flora': 'flat farmland with birch stands and pine forest',
  'signs': 'Lithuanian language signs with ogoneks and caron letters',
  'lines': 'white lines on flat straight roads with wide verges',
  'bollard': 'white posts with red reflectors along the shoulder'},
'Luxembourg': {
  'arch': 'prosperous stone and render houses with slate roofs',
  'flora': 'wooded rolling hills and small tidy pastures',
  'signs': 'French and German signs, CR and N road numbers',
  'lines': 'white lines on smooth well kept narrow roads',
  'misc': 'dense forest valleys with very tidy small villages'},
'Malta': {
  'arch': 'honey coloured limestone buildings with flat roofs',
  'flora': 'dry rocky terrain, prickly pear and low stone walls',
  'signs': 'Maltese and English bilingual signs',
  'misc': 'traffic drives on the left, very narrow walled lanes',
  'lines': 'worn markings, dry stone walls right at the road edge'},
'Monaco': {
  'arch': 'dense modern high rise apartments on a steep coast',
  'flora': 'palms and manicured mediterranean planting',
  'signs': 'French language signs in a dense urban setting',
  'misc': 'luxury cars, tunnels, multi level roads above the sea',
  'lines': 'immaculate white lines on steep urban switchbacks'},
'Montenegro': {
  'arch': 'stone houses with orange roofs, unfinished concrete',
  'flora': 'dramatic bare karst mountains meeting the Adriatic',
  'signs': 'Montenegrin signs in Latin and Cyrillic script',
  'lines': 'narrow roads with frequent guardrails above steep drops',
  'misc': 'older camera coverage, tunnels cut through bare rock'},
'Netherlands': {
  'arch': 'brick houses with large windows in neat terraces',
  'flora': 'very flat polder farmland, drainage ditches, few hills',
  'signs': 'Dutch language signs, N road numbers',
  'lines': 'red asphalt cycle paths beside white lined roads',
  'misc': 'canals, dykes, huge numbers of bicycles, wind turbines'},
'North Macedonia': {
  'arch': 'red roofed houses and unfinished concrete on hillsides',
  'flora': 'dry scrub hills, tobacco and vine fields in valleys',
  'signs': 'Macedonian Cyrillic road signs',
  'misc': 'older lower quality camera coverage, patched narrow roads',
  'lines': 'faded white lines, black and white striped kerbstones'},
'Norway': {
  'arch': 'red and white painted wooden houses with grass roofs',
  'flora': 'steep spruce forest, bare fells, fjords and waterfalls',
  'signs': 'Norwegian language signs with the letters ae, oe and aa',
  'lines': 'yellow centre lines and white edge lines',
  'misc': 'frequent long tunnels, rock cuttings, guardrails on fjord roads'},
'Poland': {
  'arch': 'square render houses with steep roofs, brick farm sheds',
  'flora': 'flat farmland in long narrow strips, birch and pine',
  'signs': 'Polish language signs with slashed l and tailed letters',
  'poles': 'concrete utility poles with distinctive cross arms',
  'lines': 'white lines on narrow roads with tree avenues',
  'bollard': 'white posts with red reflector bands'},
'Portugal': {
  'arch': 'white houses with orange roofs and azulejo tiled walls',
  'flora': 'eucalyptus and cork oak plantations, pine near the coast',
  'signs': 'Portuguese language signs, N and EN road numbers',
  'lines': 'white lines on dark tarmac, cobbled village streets',
  'misc': 'black and white cobbled pavements, many eucalyptus stands'},
'Romania': {
  'arch': 'colourful village houses with ornate metal gates',
  'flora': 'Carpathian beech and spruce forest, small hay meadows',
  'signs': 'Romanian language signs with comma below letters',
  'misc': 'orthodox churches, horse carts, older camera coverage',
  'bollard': 'black and white striped kerbstones and posts'},
'Serbia': {
  'arch': 'red roofed brick houses, unfinished upper storeys',
  'flora': 'flat Pannonian farmland in the north, wooded hills south',
  'signs': 'Serbian signs in both Cyrillic and Latin script',
  'bollard': 'black and white striped kerbstones',
  'misc': 'older camera coverage, wide flat maize fields'},
'Slovakia': {
  'arch': 'painted village houses with steep tiled roofs',
  'flora': 'Carpathian spruce forest and narrow farmed valleys',
  'signs': 'Slovak language signs with caron and acute accents',
  'bollard': 'white bollards with an orange reflector strip',
  'lines': 'white lines on narrow valley roads with tree avenues',
  'misc': 'wooded ridges rising directly behind small villages'},
'Slovenia': {
  'arch': 'alpine houses with wide eaves and white church spires',
  'flora': 'steep green forested hills, vineyards and karst meadows',
  'signs': 'Slovenian language signs with caron letters',
  'lines': 'crisp white lines on very well maintained narrow roads',
  'misc': 'hayracks in fields, onion domed church towers on hilltops'},
'Spain': {
  'arch': 'white or ochre houses with flat terracotta roofs',
  'flora': 'olive groves, dry meseta scrub and irrigated orchards',
  'signs': 'Spanish language signs, N and A road numbers',
  'lines': 'white lines on wide smooth roads through dry country',
  'misc': 'dry stone terraces, dusty verges, sparse holm oak dehesa'},
'Sweden': {
  'arch': 'falu red wooden houses with white trim',
  'flora': 'pine and spruce forest, birch stands, lakes and bogs',
  'signs': 'Swedish language signs with the letters aa, ae and oe',
  'lines': 'white lines on wide roads with tall reflector posts',
  'misc': 'long straight forest roads, rock cuttings, red barns'},
'Switzerland': {
  'arch': 'wooden chalets with wide balconies and stone farmhouses',
  'flora': 'steep alpine meadows, spruce forest and bare high peaks',
  'signs': 'German French or Italian signs, immaculate signage',
  'lines': 'flawless white lines on pristine narrow mountain roads',
  'misc': 'very clean road furniture, cable cars, hillside cow pasture'},
'Turkey': {
  'arch': 'concrete apartment blocks with solar water heaters',
  'flora': 'dry Anatolian steppe, poplar rows and irrigated fields',
  'signs': 'Turkish language signs with dotless i and cedilla letters',
  'misc': 'mosques with slim minarets, frequent red Turkish flags',
  'lines': 'white lines on wide roads, dusty gravel shoulders'},
'Ukraine': {
  'arch': 'Soviet era blocks and small render cottages',
  'flora': 'vast flat black earth farmland with poplar windbreaks',
  'signs': 'Ukrainian Cyrillic road signs',
  'poles': 'concrete utility poles along wide open plains',
  'misc': 'long straight roads, sunflower fields, worn tarmac'},
'United Kingdom': {
  'arch': 'brick terraced houses with slate roofs and chimney stacks',
  'flora': 'trimmed hedgerows, small green fields and oak trees',
  'signs': 'English language signs, distances in miles',
  'misc': 'traffic drives on the left, roundabouts and yellow kerb lines',
  'lines': 'white lines on narrow lanes enclosed by high hedges'},

# --- the rest of the world, added with the global model -------------------
'American Samoa': {
  'arch': 'open sided fale meeting houses and large white village churches',
  'flora': 'steep jungle covered volcanic slopes above a coastal road',
  'signs': 'American style road signs on a small Pacific island',
  'lines': 'yellow centre lines on a narrow road beside the sea',
  'misc': 'coconut palms, breadfruit trees and graves in front yards'},
'Argentina': {
  'arch': 'low flat roofed brick and concrete houses with front fences',
  'flora': 'flat pampas grassland with cattle fences and windbreak trees',
  'signs': 'Spanish language signs, RN and RP route markers',
  'lines': 'yellow centre lines with white edge lines on long straight roads',
  'poles': 'wooden utility poles along wide empty plains',
  'misc': 'wide dirt shoulders, old pickup trucks, a black camera car'},
'Australia': {
  'arch': 'single storey brick houses with corrugated metal roofs',
  'flora': 'eucalyptus gum trees, dry grass and red outback soil',
  'signs': 'yellow diamond warning signs, English language signs',
  'lines': 'white dashed centre lines and white edge lines',
  'bollard': 'white roadside posts with a red reflector strip',
  'misc': 'traffic drives on the left, utes and wide suburban streets'},
'Bangladesh': {
  'arch': 'unfinished brick buildings and tin roofed roadside shops',
  'flora': 'flat green rice paddies, ponds and banana plants',
  'signs': 'Bengali script on signs and shop boards',
  'lines': 'narrow raised roads with few or no markings',
  'misc': 'cycle rickshaws, green CNG auto rickshaws and crowded streets'},
'Bermuda': {
  'arch': 'pastel houses with white stepped limestone roofs',
  'flora': 'subtropical palms, hibiscus hedges and turquoise sea views',
  'signs': 'British style signs on a small island',
  'lines': 'narrow winding lanes between low stone walls',
  'misc': 'traffic drives on the left, many scooters, pink buses'},
'Bhutan': {
  'arch': 'whitewashed buildings with ornate painted wooden windows',
  'flora': 'steep forested Himalayan valleys with pine and rhododendron',
  'signs': 'Dzongkha script alongside English on signs',
  'lines': 'winding mountain roads with painted rock safety slogans',
  'misc': 'prayer flags, chortens and people in traditional dress'},
'Bolivia': {
  'arch': 'unfinished red brick and adobe houses with flat roofs',
  'flora': 'dry treeless altiplano plateau with snow peaks behind',
  'signs': 'Spanish language signs, political slogans painted on walls',
  'lines': 'faded markings on worn roads, many dirt streets',
  'misc': 'minibuses, women in bowler hats and wide skirts'},
'Botswana': {
  'arch': 'round thatched huts and small concrete block houses',
  'flora': 'flat dry Kalahari thorn scrub and pale sandy soil',
  'signs': 'English language signs, wildlife warning signs',
  'lines': 'yellow edge lines on long straight flat highways',
  'misc': 'donkeys, goats and cattle wandering beside the road'},
'Brazil': {
  'arch': 'low colourful houses with clay tile roofs behind walls and gates',
  'flora': 'red soil, tropical vegetation and sugar cane fields',
  'signs': 'Portuguese language signs, lombada speed bump warnings',
  'lines': 'double yellow centre lines with white edge lines',
  'poles': 'round concrete utility poles with many cables',
  'misc': 'speed bumps, small roadside bars, motorbikes'},
'Cambodia': {
  'arch': 'wooden houses on stilts and ornate Buddhist temple gates',
  'flora': 'flat rice paddies dotted with tall sugar palm trees',
  'signs': 'Khmer script signs, political party signboards',
  'lines': 'red dirt side roads joining a narrow paved road',
  'misc': 'motorbikes pulling trailers, tuk tuks and roadside stalls'},
'Canada': {
  'arch': 'detached houses with vinyl siding and large driveways',
  'flora': 'conifer and birch forest, lakes, wide prairie fields',
  'signs': 'English and French bilingual signs, distances in kilometres',
  'lines': 'yellow centre lines with white edge lines',
  'poles': 'tall wooden utility poles along wide roads',
  'misc': 'pickup trucks, snow banks, wide gravel shoulders'},
'Chile': {
  'arch': 'low houses with corrugated roofs, wooden houses in the south',
  'flora': 'dry hills with the Andes behind, vineyards, Atacama desert',
  'signs': 'Spanish language signs, Ruta highway shields',
  'lines': 'white lines with yellow edge markings on long highways',
  'poles': 'concrete utility poles along the roadside',
  'misc': 'a white camera truck, long thin coastal desert roads'},
'Christmas Island': {
  'arch': 'small tropical settlement with low houses and a jetty',
  'flora': 'dense rainforest, limestone cliffs and red land crabs',
  'signs': 'Australian style road signs on a jungle island',
  'lines': 'narrow unmarked roads through thick forest',
  'misc': 'footpaths, boardwalks and rocky shoreline views'},
'Colombia': {
  'arch': 'unfinished red brick houses stacked on steep hillsides',
  'flora': 'lush green Andean mountains, coffee and banana plants',
  'signs': 'Spanish language signs, yellow diamond warning signs',
  'lines': 'double yellow centre lines on winding mountain roads',
  'plates': 'bright yellow licence plates on every car',
  'misc': 'many motorbikes, colourful buses, roadside stalls'},
'Costa Rica': {
  'arch': 'low houses with corrugated metal roofs and iron window bars',
  'flora': 'dense tropical green hills, living fence posts, banana plants',
  'signs': 'Spanish language signs, ALTO stop signs',
  'lines': 'yellow centre lines on narrow roads with deep roadside ditches',
  'misc': 'small sodas and pulperia shops, overcast humid sky'},
'Curaçao': {
  'arch': 'brightly painted Dutch colonial buildings with gabled roofs',
  'flora': 'dry thorny scrub with tall cacti and divi divi trees',
  'signs': 'Dutch and Papiamentu signs',
  'lines': 'worn roads with faded markings on a flat arid island',
  'misc': 'colourful flat roofed houses, oil refinery, turquoise bays'},
'Dominican Republic': {
  'arch': 'colourful concrete houses with iron grilles and zinc roofs',
  'flora': 'royal palms, sugar cane and green tropical hills',
  'signs': 'Spanish language signs, colmado corner shops',
  'lines': 'yellow centre lines on patched roads',
  'misc': 'motorbike taxis, tangled overhead wires, roadside fruit stalls'},
'Ecuador': {
  'arch': 'unfinished concrete block houses with rebar on the roof',
  'flora': 'green Andean highlands, volcanoes, banana plantations on the coast',
  'signs': 'Spanish language signs, blue tourist signs',
  'lines': 'double yellow centre lines on mountain roads',
  'misc': 'yellow taxis, pickup trucks carrying passengers'},
'Eswatini': {
  'arch': 'scattered homesteads with round huts and tin roofed houses',
  'flora': 'rolling green hills with granite boulders and sugar cane',
  'signs': 'English language signs on a rural African road',
  'lines': 'yellow edge lines on smooth hilly highways',
  'misc': 'cattle on the verge, minibuses, people walking the roadside'},
'Faroe Islands': {
  'arch': 'colourful wooden houses, some with turf roofs',
  'flora': 'treeless steep green grassy slopes and sea cliffs',
  'signs': 'Faroese language signs with the letters eth and o slash',
  'lines': 'narrow roads with yellow edge markings and single lane tunnels',
  'misc': 'sheep on the road, fog, fjords and waterfalls'},
'Ghana': {
  'arch': 'concrete block houses, kiosks and shipping container shops',
  'flora': 'red laterite soil with oil palms and plantain',
  'signs': 'English language signs, religious shop names',
  'lines': 'open concrete drains beside worn roads',
  'misc': 'tro tro minibuses, taxis with orange corner panels, a visible roof rack'},
'Gibraltar': {
  'arch': 'dense apartment blocks and British colonial buildings',
  'flora': 'a huge limestone rock rising above the town and harbour',
  'signs': 'English language signs with British style road furniture',
  'lines': 'narrow steep streets with yellow kerb lines',
  'misc': 'red post boxes and phone boxes, traffic on the right'},
'Greenland': {
  'arch': 'brightly coloured wooden houses perched on bare rock',
  'flora': 'no trees, bare granite, icebergs floating in a fjord',
  'signs': 'Greenlandic and Danish signs',
  'lines': 'short gravel and unmarked asphalt roads in a small town',
  'misc': 'snow patches, sled dogs, pipes and wooden stairways'},
'Guam': {
  'arch': 'flat roofed concrete typhoon proof houses',
  'flora': 'tropical jungle, coconut palms and coastal cliffs',
  'signs': 'American style road signs on a Pacific island',
  'lines': 'yellow centre lines on wide pale coral asphalt roads',
  'poles': 'thick concrete utility poles',
  'misc': 'American pickup trucks, strip malls, military fences'},
'Guatemala': {
  'arch': 'concrete block houses with corrugated metal roofs',
  'flora': 'green highlands with volcano cones and maize fields',
  'signs': 'Spanish language signs, hand painted shop walls',
  'lines': 'yellow centre lines on winding highland roads',
  'misc': 'brightly painted chicken buses, tuk tuks, speed bumps'},
'Hong Kong': {
  'arch': 'extremely dense forest of tall narrow apartment towers',
  'flora': 'steep green subtropical hills right behind the city',
  'signs': 'traditional Chinese and English bilingual signs',
  'lines': 'yellow road markings, zigzag lines and railings at the kerb',
  'misc': 'double decker buses, red taxis, traffic on the left'},
'India': {
  'arch': 'painted concrete buildings with shop shutters and water tanks',
  'flora': 'dusty plains, banyan and neem trees, palm trees in the south',
  'signs': 'Hindi or regional script alongside English',
  'bollard': 'black and yellow striped kerbs and road dividers',
  'lines': 'white lines on crowded roads with unpaved edges',
  'misc': 'auto rickshaws, cows on the road, decorated trucks'},
'Indonesia': {
  'arch': 'low houses with red clay tile roofs and tiled porches',
  'flora': 'rice terraces, coconut palms and banana plants',
  'signs': 'Indonesian language signs, Jalan street names',
  'bollard': 'black and white striped kerbs',
  'lines': 'white lines on narrow roads crowded with scooters',
  'misc': 'swarms of scooters, small warung stalls, traffic on the left'},
'Isle of Man': {
  'arch': 'grey stone cottages and Victorian seafront terraces',
  'flora': 'green hills, gorse hedges and dry stone walls',
  'signs': 'British style signs on a small island',
  'bollard': 'black and white painted kerbs on racing road bends',
  'lines': 'white lines on narrow hedged lanes, traffic on the left'},
'Israel': {
  'arch': 'pale stone apartment blocks with solar water tanks on the roofs',
  'flora': 'dry rocky hills with pine, olive and cypress trees',
  'signs': 'Hebrew, Arabic and English trilingual signs',
  'lines': 'yellow edge lines with white centre lines',
  'plates': 'long yellow licence plates',
  'bollard': 'red and white striped kerbs'},
'Japan': {
  'arch': 'compact houses with grey tiled roofs packed close together',
  'flora': 'forested mountains, cedar woods and flooded rice paddies',
  'signs': 'Japanese kanji and kana signs, blue circular mirrors',
  'poles': 'utility poles with yellow and black striped guards and dense wires',
  'lines': 'narrow streets with white edge lines and no pavement',
  'misc': 'tiny kei cars, vending machines, traffic on the left'},
'Jersey': {
  'arch': 'pink granite farmhouses and cottages',
  'flora': 'narrow lanes sunk between high hedge banks and granite walls',
  'signs': 'British style signs with French road names',
  'lines': 'yellow line across the road at junctions',
  'misc': 'traffic on the left, small fields, glimpses of the sea'},
'Jordan': {
  'arch': 'boxy beige limestone buildings with white water tanks on top',
  'flora': 'barren rocky desert hills with scattered olive trees',
  'signs': 'Arabic and English bilingual signs',
  'lines': 'yellow edge lines on wide desert highways',
  'misc': 'unfinished concrete pillars on roofs, speed bumps, dust'},
'Kazakhstan': {
  'arch': 'Soviet apartment blocks and low houses behind metal fences',
  'flora': 'vast flat treeless steppe to the horizon',
  'signs': 'Cyrillic signs in Kazakh and Russian',
  'lines': 'white lines on very long straight roads',
  'misc': 'old Soviet cars, roadside cemeteries, a visible roof rack'},
'Kenya': {
  'arch': 'tin roofed shops painted in bright advertising colours',
  'flora': 'red soil, acacia trees and dry savanna',
  'signs': 'English and Swahili signs',
  'lines': 'yellow edge lines on worn tarmac with dirt shoulders',
  'misc': 'matatu minibuses, motorbike taxis, a snorkel on the camera car'},
'Kosovo': {
  'arch': 'large unfinished red brick houses with no render',
  'flora': 'green rolling hills and plains ringed by mountains',
  'signs': 'Albanian and Serbian bilingual signs',
  'lines': 'white lines on newly built roads',
  'misc': 'minarets in villages, Albanian flags, car washes and petrol stations'},
'Kyrgyzstan': {
  'arch': 'old village houses with blue painted window frames and fences',
  'flora': 'snow capped Tian Shan mountains above dry valleys, poplar rows',
  'signs': 'Cyrillic signs in Kyrgyz and Russian',
  'lines': 'worn roads lined with white painted tree trunks',
  'misc': 'horses and sheep on the road, yurts, a visible roof rack'},
'Laos': {
  'arch': 'wooden stilt houses and gilded Buddhist temples',
  'flora': 'jungle covered karst hills and red dirt',
  'signs': 'Lao script signs',
  'lines': 'narrow paved road with red dirt edges and few markings',
  'misc': 'scooters, roaming chickens and dogs, Beerlao signs'},
'Lebanon': {
  'arch': 'dense concrete apartment blocks climbing steep hillsides',
  'flora': 'Mediterranean mountains with pines and terraces',
  'signs': 'Arabic and French signs',
  'poles': 'tangled overhead electricity wires across the street',
  'misc': 'old Mercedes taxis, political posters, roadside billboards'},
'Lesotho': {
  'arch': 'round stone huts with thatched roofs',
  'flora': 'treeless high grassy mountains and eroded gullies',
  'signs': 'English and Sesotho signs',
  'lines': 'winding mountain passes with yellow edge lines',
  'misc': 'herders wrapped in blankets, people on horseback'},
'Macau': {
  'arch': 'huge casino hotels beside old crowded apartment blocks',
  'flora': 'dense city with banyan trees in small squares',
  'signs': 'Chinese and Portuguese bilingual street signs on blue tiles',
  'lines': 'black and white wave pattern mosaic pavements',
  'plates': 'black licence plates with white letters',
  'misc': 'rows of parked scooters, traffic on the left'},
'Madagascar': {
  'arch': 'tall narrow red brick houses with steep roofs',
  'flora': 'red laterite earth, rice paddies and bare eroded hills',
  'signs': 'French and Malagasy signs',
  'lines': 'potholed roads and dirt tracks without markings',
  'misc': 'zebu carts, pousse pousse rickshaws, wooden market stalls'},
'Malaysia': {
  'arch': 'rows of terraced shophouses and houses with tiled roofs',
  'flora': 'endless oil palm plantations and jungle hills',
  'signs': 'Malay language signs, Jalan street names',
  'bollard': 'black and white striped kerbs',
  'plates': 'black licence plates with white letters',
  'misc': 'traffic on the left, small motorbikes, mosques with domes'},
'Mexico': {
  'arch': 'colourful flat roofed concrete houses with rebar sticking up',
  'flora': 'dry scrub with cactus and agave, dusty hills',
  'signs': 'Spanish language signs, ALTO stop signs',
  'lines': 'yellow centre lines, frequent tope speed bumps',
  'misc': 'black rooftop water tanks, taco stands, painted shop walls'},
'Mongolia': {
  'arch': 'white felt gers and wooden fenced compounds',
  'flora': 'vast treeless grassy steppe and bare hills',
  'signs': 'Mongolian Cyrillic signs',
  'lines': 'dirt tracks crossing open grassland',
  'misc': 'herds of horses, camping gear strapped to the camera car roof'},
'Namibia': {
  'arch': 'German colonial buildings and tin roofed houses',
  'flora': 'desert plains, dry thorn savanna and rocky hills',
  'signs': 'English language signs, wildlife warning signs',
  'lines': 'wide straight gravel roads raising dust',
  'misc': 'endless wire fences, huge empty landscapes, traffic on the left'},
'Nepal': {
  'arch': 'colourful multi storey concrete houses with roof terraces',
  'flora': 'terraced Himalayan hillsides and snow peaks',
  'signs': 'Devanagari script signs',
  'lines': 'rough broken mountain roads with dust and rubble',
  'misc': 'decorated trucks and buses, prayer flags, motorbikes'},
'New Zealand': {
  'arch': 'wooden weatherboard houses with corrugated iron roofs',
  'flora': 'bright green sheep pasture on steep hills, tree ferns',
  'signs': 'yellow diamond warning signs, English and Maori place names',
  'bollard': 'white roadside posts with a red reflector band',
  'lines': 'white centre lines with yellow no overtaking lines',
  'misc': 'one lane bridges, traffic on the left, wire farm fences'},
'Nigeria': {
  'arch': 'walled compounds and concrete buildings with rusty tin roofs',
  'flora': 'red soil with palms and dense green bush',
  'signs': 'English language signs, church and school billboards',
  'lines': 'worn roads with open gutters and sandy edges',
  'misc': 'yellow minibuses and tricycles, a police escort car following'},
'Northern Mariana Islands': {
  'arch': 'low concrete houses and resort hotels by the beach',
  'flora': 'tropical jungle, flame trees and turquoise lagoon',
  'signs': 'American style road signs on a small tropical island',
  'lines': 'yellow centre lines on quiet coastal roads',
  'misc': 'wartime bunkers and memorials, beach parks'},
'Oman': {
  'arch': 'white flat roofed villas with crenellated walls and arches',
  'flora': 'barren brown rocky mountains and date palm oases',
  'signs': 'Arabic and English bilingual signs',
  'lines': 'smooth highways with yellow edge lines and rows of street lights',
  'misc': 'white SUVs, mosques with small domes, gravel desert'},
'Palestine': {
  'arch': 'pale stone houses with black water tanks on flat roofs',
  'flora': 'terraced rocky hills with olive groves',
  'signs': 'Arabic signs, some with Hebrew and English',
  'plates': 'white licence plates with green letters',
  'misc': 'minarets, yellow taxis, unfinished upper floors'},
'Panama': {
  'arch': 'low houses with zinc roofs, glass skyscrapers in the city',
  'flora': 'humid tropical forest and green cattle pasture',
  'signs': 'Spanish language signs in American highway style',
  'lines': 'yellow centre lines on concrete slab roads',
  'misc': 'painted old school buses, yellow taxis'},
'Paraguay': {
  'arch': 'low brick houses with tiled porches and shady yards',
  'flora': 'red earth, flat subtropical farmland and palm trees',
  'signs': 'Spanish language signs',
  'lines': 'rough cobblestone side streets beside red dirt roads',
  'misc': 'motorbikes, roadside terere stalls, cattle ranches'},
'Peru': {
  'arch': 'unfinished brick and adobe houses with rebar on flat roofs',
  'flora': 'bare coastal desert or dry Andean valleys',
  'signs': 'Spanish language signs, election slogans painted on walls',
  'lines': 'yellow centre lines on dusty roads',
  'misc': 'three wheeled mototaxis, combi minibuses'},
'Philippines': {
  'arch': 'concrete houses with corrugated roofs behind painted walls',
  'flora': 'coconut palms, banana plants and rice fields',
  'signs': 'English and Tagalog signs, sari sari store boards',
  'lines': 'pale concrete slab roads with visible joints',
  'poles': 'leaning poles with tangled bundles of wires',
  'misc': 'jeepneys and motorbike sidecar tricycles'},
'Puerto Rico': {
  'arch': 'flat roofed concrete houses with iron grilles in bright colours',
  'flora': 'steep green tropical hills with palms and flamboyant trees',
  'signs': 'American style road signs written in Spanish',
  'lines': 'yellow centre lines on narrow winding hill roads',
  'misc': 'kilometre markers, roadside food kiosks, American cars'},
'Qatar': {
  'arch': 'beige walled villas and glass skyscrapers',
  'flora': 'flat pale desert with planted date palms',
  'signs': 'Arabic and English bilingual signs',
  'lines': 'wide new multi lane highways with ornate street lights',
  'misc': 'white SUVs, construction sites, sandy empty plots'},
'Russia': {
  'arch': 'wooden village houses with carved window frames, grey panel blocks',
  'flora': 'birch and pine forest, wide flat fields',
  'signs': 'Russian Cyrillic signs, blue direction signs',
  'bollard': 'black and white striped posts and kerbs',
  'lines': 'white lines on wide roads with muddy verges',
  'misc': 'Lada cars, overhead gas pipes, a visible roof antenna'},
'Rwanda': {
  'arch': 'small brick houses with tin roofs on hillsides',
  'flora': 'green terraced hills with banana plants and eucalyptus',
  'signs': 'English, French and Kinyarwanda signs',
  'lines': 'very clean roads with neat kerbs and trimmed verges',
  'misc': 'motorcycle taxis with helmets, people carrying loads on bicycles'},
'Réunion': {
  'arch': 'creole houses with tin roofs and wooden trim',
  'flora': 'sugar cane fields below steep volcanic mountains',
  'signs': 'French road signs and road furniture on a tropical island',
  'bollard': 'French style white bollards with a red band',
  'misc': 'French licence plates, palm trees, clouds on the peaks'},
'San Marino': {
  'arch': 'stone old town with fortress towers on a cliff top',
  'flora': 'green rolling hills seen from high above',
  'signs': 'Italian language signs',
  'lines': 'steep winding roads with stone retaining walls',
  'plates': 'white licence plates with blue letters and a coat of arms'},
'Senegal': {
  'arch': 'flat roofed concrete block buildings and walled compounds',
  'flora': 'dry sandy Sahel with baobab and acacia trees',
  'signs': 'French language signs',
  'lines': 'sand drifting over the edges of paved roads',
  'misc': 'horse carts, colourful painted minibuses, yellow and black taxis'},
'Singapore': {
  'arch': 'tall public housing blocks with numbers painted on the side',
  'flora': 'lush rain trees arching over spotless roads',
  'signs': 'English language signs, green street name signs',
  'lines': 'double yellow and zigzag lines along the kerb',
  'plates': 'black licence plates with white letters',
  'misc': 'traffic on the left, covered walkways, overhead toll gantries'},
'South Africa': {
  'arch': 'walled houses with electric fences, tin shack townships',
  'flora': 'dry veld grassland, flat topped hills, fynbos scrub',
  'signs': 'English and Afrikaans signs, white on green direction signs',
  'lines': 'yellow edge lines with white centre lines',
  'misc': 'minibus taxis, pickup trucks, traffic on the left'},
'South Korea': {
  'arch': 'rows of identical tall apartment towers, blue and orange metal roofs',
  'flora': 'forested hills, rice paddies and plastic greenhouses',
  'signs': 'Korean Hangul signs',
  'lines': 'yellow centre lines, blue bus lane lines',
  'misc': 'convex mirrors, speed cameras, white and grey sedans'},
'Sri Lanka': {
  'arch': 'low houses with red tile roofs and verandas behind garden walls',
  'flora': 'lush coconut palms, banana plants and tea covered hills',
  'signs': 'Sinhala, Tamil and English trilingual signs',
  'lines': 'white dashed centre line on narrow busy roads',
  'misc': 'tuk tuks, red public buses, traffic on the left'},
'Svalbard': {
  'arch': 'colourful wooden houses raised on stilts above the ground',
  'flora': 'arctic tundra with no trees, bare mountains and glaciers',
  'signs': 'Norwegian signs, polar bear warning signs',
  'lines': 'gravel roads beside pipes running above ground',
  'misc': 'snowmobiles parked outside houses, old mining structures'},
'São Tomé and Príncipe': {
  'arch': 'crumbling Portuguese colonial plantation buildings, wooden stilt houses',
  'flora': 'dense tropical rainforest on steep volcanic peaks',
  'signs': 'Portuguese language signs',
  'lines': 'narrow potholed coastal roads without markings',
  'misc': 'yellow taxis, laundry drying on the ground, fishing canoes'},
'Taiwan': {
  'arch': 'concrete shophouses with covered arcades and metal roof sheds',
  'flora': 'steep green mountains, betel nut palms and rice paddies',
  'signs': 'traditional Chinese signs, dense vertical shop signs',
  'lines': 'yellow centre lines, red painted kerbs',
  'poles': 'utility poles wrapped in yellow and black stripes',
  'misc': 'swarms of scooters and rows of them parked on the street'},
'Thailand': {
  'arch': 'spirit houses on posts, gilded temples with steep red roofs',
  'flora': 'palm trees, rice paddies and tropical greenery',
  'signs': 'Thai script signs, portraits of the king over the road',
  'lines': 'yellow centre lines with white edge lines',
  'poles': 'square concrete utility poles',
  'misc': 'pickup trucks, scooters, traffic on the left'},
'Tunisia': {
  'arch': 'white cubic houses with blue doors and shutters',
  'flora': 'olive groves, prickly pear hedges and dry plains',
  'signs': 'Arabic and French bilingual signs',
  'bollard': 'red and white painted kerbs',
  'plates': 'black licence plates with white Arabic script',
  'misc': 'yellow taxis, unfinished brick upper floors'},
'US Virgin Islands': {
  'arch': 'colourful Caribbean houses with hipped roofs on steep slopes',
  'flora': 'green hills dropping to turquoise bays, palms and sea grape',
  'signs': 'American style road signs on a Caribbean island',
  'lines': 'yellow centre lines with traffic on the left in American cars',
  'misc': 'open air safari taxis, steep switchback roads'},
'Uganda': {
  'arch': 'shops painted in bright advertising colours with tin roofs',
  'flora': 'red soil and lush green banana plants',
  'signs': 'English language signs, school and church signposts',
  'lines': 'red dirt shoulders beside a paved road',
  'misc': 'boda boda motorbike taxis, people selling goods at the roadside'},
'United Arab Emirates': {
  'arch': 'glass skyscrapers and white walled villas',
  'flora': 'orange sand dunes and planted date palms',
  'signs': 'Arabic and English bilingual signs',
  'lines': 'very wide multi lane highways with rows of street lights',
  'misc': 'white SUVs, mosques, construction cranes'},
'United States': {
  'arch': 'detached wooden houses with front lawns and no fences',
  'flora': 'wide open landscapes, farmland, forest or desert',
  'signs': 'English language signs, green highway signs with distances in miles',
  'lines': 'double yellow centre lines with white edge lines',
  'poles': 'wooden utility poles along wide roads',
  'misc': 'pickup trucks, mailboxes at the roadside, yellow school buses'},
'Uruguay': {
  'arch': 'low flat roofed houses with small front gardens',
  'flora': 'gently rolling green pasture with cattle and eucalyptus stands',
  'signs': 'Spanish language signs, Ruta highway markers',
  'lines': 'white lines on quiet two lane roads',
  'misc': 'old cars, palm trees along the coast, wire farm fences'},
'Vietnam': {
  'arch': 'tall narrow tube houses with balconies',
  'flora': 'rice paddies, limestone karst peaks and palms',
  'signs': 'Vietnamese signs in Latin script with many accent marks',
  'lines': 'yellow centre lines on roads crowded with motorbikes',
  'misc': 'red flags with a yellow star, street vendors in conical hats'},
}

TEMPLATE = 'a Google Street View photo taken in {c}, {cue}'
PLAIN    = 'a Google Street View photo taken in {c}'


def country_captions(country):
    """Several short captions per country, each within CLIP's 77 tokens."""
    caps = [PLAIN.format(c=country)]
    for cue in GEOTIPS.get(country, {}).values():
        caps.append(TEMPLATE.format(c=country, cue=cue))
    return caps


def plain_captions(country):
    """The simple baseline, for measuring what the rich prompts add."""
    return [PLAIN.format(c=country)]
