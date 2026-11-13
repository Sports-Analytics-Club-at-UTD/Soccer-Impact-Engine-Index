// Build-time admission only. This module is never imported by browser code.
// Only the explicitly reviewed public final-ratings release is admitted.
// Environment flags and self-declared payload booleans cannot add authority.
import { PUBLIC_RATINGS_RELEASE } from '../src/lib/publicRatingsRelease.js';
import { PLAYER_PORTRAIT_ASSETS } from './playerPortraitAssets.js';
import { createHash } from 'node:crypto';
import { lstat, readFile, readdir, realpath } from 'node:fs/promises';
import { basename, dirname, extname, isAbsolute, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const FRONTEND_ROOT = fileURLToPath(new URL('../', import.meta.url));
const REPOSITORY_ROOT = resolve(FRONTEND_ROOT, '..');
const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
const denied = (reason) => { throw Error(`Production data admission denied: ${reason}`); };

// Existing aggregate team pictures are retained unchanged; this is an asset
// inventory, not certification of their statistical provenance. New static/demo
// assets require explicit path/content review here. Never add private data here.
export const PUBLIC_ASSETS = Object.freeze([
  PUBLIC_RATINGS_RELEASE,
  // Reviewed portrait identities; sources accompany the PNGs.
  ...PLAYER_PORTRAIT_ASSETS,
  // Club crests retrieved from the official sites; sources accompany the SVGs.
  { path: 'team/crests/psg.svg', sha256: '75681805ff4dd4f84e4e489c1c4c6a459834cf9e4c2d1689b5b2638a952a1324' },
  { path: 'team/crests/barca.svg', sha256: 'dc8dda5ee534f1da22370228d9bc5881459c1054b4755426d7410df1d9db3e22' },
  { path: 'team/crests/leverkusen.svg', sha256: '9bc73ca2ee27332a2b8f391795516587aa65fc1b7b321e360771402d64eed6ad' },
  { path: 'team/crests/ac-milan.png', sha256: '32f172036837a0a4a7ef3aadd67f2f3d5cb9f697b698ff6c7722b42faa8ae42e' },
  { path: 'team/crests/afc-bournemouth.png', sha256: '0383002b303b31fd4672b7823672c472660be4f2175d84ac480a26e1a06e61bb' },
  { path: 'team/crests/angers.png', sha256: '112434f38848350bc1747b84c0a85e7a5230e8bee185b3da27e91ddebde02193' },
  { path: 'team/crests/arsenal.png', sha256: '92f1bb35662ff56dde09e1f8084221a458357a6df390bc97b2ed6495f6e39f53' },
  { path: 'team/crests/as-monaco.png', sha256: 'bd23a74bdca89df5ed4876567478e5f08e82a4d6576e0252f16968f266300d64' },
  { path: 'team/crests/as-roma.png', sha256: '5c8d62dad1ad929922adbb87877f582d8eb0d18c2b76e40facedc2eee65e9a2f' },
  { path: 'team/crests/aston-villa.png', sha256: 'aad2e636ade60b485855deacfe74f831c8dcae46de72079c7f521b06c1b5865b' },
  { path: 'team/crests/atalanta.png', sha256: 'd3626b9d4f0fd313cc101ab5013c4d872713786d1ece24361329059ea37134f6' },
  { path: 'team/crests/athletic-club.png', sha256: 'ce67012de7d0cef9323bb2afd7481258eee4c927ae1a4f2b9fd156ef66800eec' },
  { path: 'team/crests/atletico-madrid.png', sha256: '00e98bfb76fe09a385afc20f73ae0f9ac076f9a22cc559d32cee30fd492f0f10' },
  { path: 'team/crests/bastia.png', sha256: 'dcbf6da81d6edeae581277f0a9eda232ddcfc1067d24f15f6fd8b7a7dc6287c0' },
  { path: 'team/crests/bayern-munich.png', sha256: '97d9c68c3fbc44834e836b6b82afab725e450d0a7c5f5d6a328f4888297511ed' },
  { path: 'team/crests/bologna.png', sha256: 'b7e9f6c4b3bec908c40315995fcf54dcc2d61997dd1daa2cc1263259f3aa231e' },
  { path: 'team/crests/bordeaux.png', sha256: '4c5f7b52060d02581c019ed9c6116ae1b8fc96e80545ac4835107602c1024915' },
  { path: 'team/crests/borussia-dortmund.png', sha256: 'bd11d3d9f17caf5352cb44234961b89b8794a453b2fa9c355586b68a828facd8' },
  { path: 'team/crests/borussia-monchengladbach.png', sha256: '6c25f5093b31fead98e8149f1aed4ce9d8c2f41fb19eaade48111bd17afa6a48' },
  { path: 'team/crests/caen.png', sha256: '3a230e1f275692989719325229fda7ca7504c345ef081f39a698dbe72252ec47' },
  { path: 'team/crests/carpi.png', sha256: 'f5749c3c26201e8e2941a6dc569fafed564e0455c4f355bc0492cc77dd0f20aa' },
  { path: 'team/crests/celta-vigo.png', sha256: '3b539c13d57dd1e21c1c2c7f7347e5b3433cb03ed966eceec381ff4c1ff1e434' },
  { path: 'team/crests/chelsea.png', sha256: '6f14d86b5e35074e91462c7ede6e822f6a6c9f6cb723cd04ea6b8d36f2fa5392' },
  { path: 'team/crests/chievo-verona.png', sha256: 'efac7767ec4d7343b69b782c073445af98e6774242c319e06d119fe8f2747300' },
  { path: 'team/crests/crystal-palace.png', sha256: 'bc829f12cbd54aa1116888d68fda2cfe8bf4c16adea80033af748ca54a153920' },
  { path: 'team/crests/deportivo.png', sha256: '5f4255c6a0e0773c29fe1291390bb4ed4548f67e5f3fa249340d87af49967ccb' },
  { path: 'team/crests/eibar.png', sha256: '72f406ce5cb961a94b0f5540a82bfeb3e71d8bbf8df7378ae4eda21463f6a587' },
  { path: 'team/crests/eintracht-frankfurt.png', sha256: '8ed093c2fc6ef46b7cc8e8ac58b0dd7f8fccbae719cba7514dffe7c40507f16c' },
  { path: 'team/crests/empoli.png', sha256: '5e6cbdb5f4ce6fedcaa39de3ad4e798a3b68dcdd7ed9a55730febc4dcc3c8ec1' },
  { path: 'team/crests/espanyol.png', sha256: '1b176c3f83401de41dc550160132b4cc777f9b5d74e68b52cd23e487277f5349' },
  { path: 'team/crests/everton.png', sha256: 'eaedbe5e3b18ddef08c09d07fdca62bcac65165b7bb9af4780acce36841aee20' },
  { path: 'team/crests/fc-augsburg.png', sha256: '15defdc0576d2d60161d16b685c026e262de42f164a20cc8a191bfc685216581' },
  { path: 'team/crests/fc-cologne.png', sha256: '180137781f4086f4f459f99ab4672d4b8904d4e997327f3fd640349d182ee058' },
  { path: 'team/crests/fc-ingolstadt-04.png', sha256: '75a8fdeb06bf10206bb0afc4c7e7ae0ee1c4f5de428abf3369d4d3c8336a4555' },
  { path: 'team/crests/fiorentina.png', sha256: 'df0a545d8a7a51b6a8f7377c9fee771aea608ca0a98cad5fda114c2043a36b85' },
  { path: 'team/crests/frosinone.png', sha256: '2db80a1a58ec56eca422f861b1be12d1c6fc3f89da4a987f20aef6c048aeb669' },
  { path: 'team/crests/genoa.png', sha256: 'a696eac5d0cb3de16effd38280997078876fd5a563b767838f88b983e70bcc27' },
  { path: 'team/crests/getafe.png', sha256: '24aa11bf23482930aa446cc8a60961dc2fa1a8efb21c89f51b0b866c6bd68ff8' },
  { path: 'team/crests/gfc-ajaccio.png', sha256: '0964509f7e589a675b8ce6766da296f8e432d722eb48924ea0e2c327dd3d6732' },
  { path: 'team/crests/granada.png', sha256: '9e7b33f21df60969607912b742ffb4757ae697dc739653ca95449af864dbea54' },
  { path: 'team/crests/guingamp.png', sha256: 'e4d46f09a7476fab31f2e9e6e11f13b8d87c5ed7d2722f06cc66ada6f9bc336f' },
  { path: 'team/crests/hamburg-sv.png', sha256: '39f948aa09e784443c3546f2248c19dfb1c15c19ecef3e588efc3128faa00a07' },
  { path: 'team/crests/hannover-96.png', sha256: 'c7ca927ecf3e110f3300423d4605e6d829e6d26b79e1697861f49861d7f3cb7a' },
  { path: 'team/crests/hellas-verona.png', sha256: '24513d6df4b5b4d56aa1fe9d1a5ccd0ab706b107e9bbd6fb6eb14f797204d433' },
  { path: 'team/crests/hertha-berlin.png', sha256: 'e9bf77b96189cfbb852fe9cbd66cd804d05c493990943803273604f1f8947393' },
  { path: 'team/crests/internazionale.png', sha256: '3020e0fba5c9391d6e8fa119ad67b93f1ad2fa77a2939a5dd42320495fd477a4' },
  { path: 'team/crests/juventus.png', sha256: '6c190f73f8913b8d0c040e5773c377517a2e1e2e76b8145c87d73c3d2a9a87d3' },
  { path: 'team/crests/las-palmas.png', sha256: '9bc3e51fafee32c1b82c4ed3f7dc51c8baa1e8635f0c4b31dc83b5e896f8ae67' },
  { path: 'team/crests/lazio.png', sha256: '774df8a00d798e0647dd8198ab0bdc27fda7daf3ca5ffbea0870f2b653d3cfe1' },
  { path: 'team/crests/leicester-city.png', sha256: 'a21568e549d0f9389f56469b75d0866281a39c1e32f37a4908c2727e0a53050f' },
  { path: 'team/crests/levante.png', sha256: '2e50213517306c537d11929055c7bd01eb8d809854a63f78e0a29a0d09ae8de8' },
  { path: 'team/crests/lille.png', sha256: '95e0ee084cb4f8cd14407aa8a75e0db932d4f0558cd3a1dfac72f293cca86e69' },
  { path: 'team/crests/liverpool.png', sha256: '9f2c56faf3631eb32fb5cccd84d31827ba38fcd9dd3280f597b221711a8797de' },
  { path: 'team/crests/lorient.png', sha256: 'e9aad5b8eac3ee5cb87908729d39572dd0799824dcb17c41fea8df0102be731f' },
  { path: 'team/crests/lyon.png', sha256: '8d19c1378008637e0f7a75c4a56bd82610c719ae3bfdcb7c1305edfe81710bcf' },
  { path: 'team/crests/mainz.png', sha256: '49d8054439ee37df533c9c88b9409c72a23647fdb7a9912d8d743482e4faced9' },
  { path: 'team/crests/malaga.png', sha256: '70c57c651fd431e97019c1c65234ce15e28a52a25abf9d11516eede56bb450a4' },
  { path: 'team/crests/manchester-city.png', sha256: '70e005bdab0ada41a153760398b4a2ef99f956bf9e72954686caa70da8c30c0b' },
  { path: 'team/crests/manchester-united.png', sha256: '03486cf5cf90d580d6132ab115cc747be7b2e3519fd6e08be56675cf5897f0b7' },
  { path: 'team/crests/marseille.png', sha256: '55fde2ea6f3e0524ae9226ccbf9240cf1cc6f49f6a402ed444b147558040428e' },
  { path: 'team/crests/montpellier.png', sha256: '7a7586bc1cd733924df4e0bd80b5dbc90f988a296a5e8bdb7284fe0ba6915976' },
  { path: 'team/crests/nantes.png', sha256: '3c88182d0c5c80be69504de2f9a68b1c84f80612a1112e91a4a0a294dfc70501' },
  { path: 'team/crests/napoli.png', sha256: 'e871ac8b6d9cf7acd850bfcf8e22e20d6258f55a45cf97023d937c5bdb515b4f' },
  { path: 'team/crests/newcastle-united.png', sha256: '5e926d9f8c18b1b20e2e86a830ad56d4a9094673f172c0f8fabf617917e1910d' },
  { path: 'team/crests/nice.png', sha256: '4d799a2e63732e66bb9e447fa8f036440c48091621ca2e97c001c14eaa758fe8' },
  { path: 'team/crests/norwich-city.png', sha256: 'd06b8b8d06c49ed01f36d4936052151c22b16ccaf27cae77dfd32c7df68b9451' },
  { path: 'team/crests/palermo.png', sha256: '43a2d80a776cf985d618a8d2d461b4ae3a786bba5a0af173f93ac51e869e6786' },
  { path: 'team/crests/rayo-vallecano.png', sha256: '66aee2a6712de83310002c53c7b361a816b0d325f3944bbf3b9d728d6ed04251' },
  { path: 'team/crests/real-betis.png', sha256: '8a2e9a3db45280f3aa8be1737e140333493828c94c98283a5bcad458529369a6' },
  { path: 'team/crests/real-madrid.png', sha256: 'acdcaaf2c60c3cc65a270dac1bd59f3a2b52911b8c45510d4e7f86d47ed714ba' },
  { path: 'team/crests/real-sociedad.png', sha256: '87b985ea790b3155b84fd5f09fdbc38b0da7853c4c61942eeaadbe2aa1db2d9c' },
  { path: 'team/crests/saint-etienne.png', sha256: '41be9b059d21849f32a69f824d46e972f9ed41b240a3c186821f624316b8e98d' },
  { path: 'team/crests/sampdoria.png', sha256: 'f2c29411659c4a3bf5a1aac0ff0cbac16b6842d6b1156e0846f45265d83d542e' },
  { path: 'team/crests/sassuolo.png', sha256: '8b941afda4d138ffcc751c3cac8ac568c82430b7a880968dda0dc92b02428121' },
  { path: 'team/crests/schalke-04.png', sha256: 'f938aab67187c8f154ad5da75cd41867bc92b5b4c0fbd9de0ac758df42d560a1' },
  { path: 'team/crests/sevilla.png', sha256: '992624b39a65ae153e9754ba302596d234faafe95062ca5d9b3095ac56211988' },
  { path: 'team/crests/southampton.png', sha256: '09b41343b46d3941a946ce5c2696550ec654d54614b7dbd22cef0cde91970335' },
  { path: 'team/crests/sporting-gijon.png', sha256: '4fecbd54531e221c40453b6450ca8ab43ac2ae08808755b9788f020d22ea71c9' },
  { path: 'team/crests/stade-de-reims.png', sha256: '49d3506b05792934f16681abb6a7aacb152d8056d10fb2114f0f4e8cbe279c32' },
  { path: 'team/crests/stade-rennais.png', sha256: '899d5d3df75bc0dba315d1bc81dcbf5b637dec04153f2491483fb4ba30412abc' },
  { path: 'team/crests/stoke-city.png', sha256: 'b02f23df8c991e3d0537f54746767f685029f766ffd72990c004f1c0f2aff8c2' },
  { path: 'team/crests/sunderland.png', sha256: 'aee718a79be592a8bb36ab68b0960a1dbb5763692f4d91c3f4249f95edbf19af' },
  { path: 'team/crests/sv-darmstadt-98.png', sha256: 'deb7bea3ebc026be2a8019e4d8fd9cc369c2a629895a8f448366b8147f592c0a' },
  { path: 'team/crests/swansea-city.png', sha256: '5fcea5a909ca225a5389ea59b3f110c7826ac9449ba11e1fbf74d6433cae57aa' },
  { path: 'team/crests/torino.png', sha256: '24bacdd110ee8a4a3599c120e81db8b002c375c5c08c95cd3d7bd41e93f84046' },
  { path: 'team/crests/tottenham-hotspur.png', sha256: 'f66f956414b0fd99df6a7e29bed0bd8a849f11d41bd749a1e08ff8d032570d35' },
  { path: 'team/crests/toulouse.png', sha256: '53782a7e221353360a53eef230873478ffe5454eb5afe771b1163376fbc5614f' },
  { path: 'team/crests/troyes.png', sha256: '34049d3fb98cc26bde433a4f28a0ebfb584a8e3b8d770eb6bc03f2cef06e08ad' },
  { path: 'team/crests/tsg-hoffenheim.png', sha256: '8fe1207f20c067ae8be9f8af4ce4e622824f9d392691df43c2d7c4cfc43b5462' },
  { path: 'team/crests/udinese.png', sha256: 'f9acfd56f4ffb566c583319cd9e2cfd0d66d2c77fa5a8cbfd96f1301b4a29ce7' },
  { path: 'team/crests/valencia.png', sha256: '4961f443b5d247b7a1ba5e2cc51bdea51633c4c0fe50a78f260e6f03b438b134' },
  { path: 'team/crests/vfb-stuttgart.png', sha256: '8a32c1caf1e7ebbd41e52ad28d3781002a789ab12826479b6abbbe78ec77c86b' },
  { path: 'team/crests/vfl-wolfsburg.png', sha256: '3b1fa2d287ae714fa460760596f14467b458c9d9748ce08bc5c813ff77443cf0' },
  { path: 'team/crests/villarreal.png', sha256: '69c1768ac26ad66621c5133c1ad5788cec94fc3ab7ad5645c23db16c37617539' },
  { path: 'team/crests/watford.png', sha256: 'd197bf6055579351059aa35603d60efeda1dd366463f3c7f9004bbf9e566c747' },
  { path: 'team/crests/werder-bremen.png', sha256: '54937bfaf99876aef4942503e6131368294f32ad01ec6d04e1b8ac08ec9f91fe' },
  { path: 'team/crests/west-bromwich-albion.png', sha256: '52bd64391405c0b43683fd419a8182eeebd33cbece1fe556a12e3de5ec775220' },
  { path: 'team/crests/west-ham-united.png', sha256: '4e74106a88addf17a9f3f0af437cd9d85c28759e93e10da0f27dd00184c234b8' },
  // About Us portraits supplied for public display.
  { path: 'team/vibhor-rajan.webp', sha256: '332f351b2fbec6b8ef4abfdde62df0efde17e61d4c66e1bd0e18f9b6b7e6e08a' },
  { path: 'team/pratyush-malaviya.webp', sha256: '9e1c95d5b3627f899f22391c0cb3dc02a13d4aee1d2ffd203993011e0095b195' },
  { path: 'team/arpit-gupta.webp', sha256: '4a0c8cfa0dd51589cc728794047cb71d91eaf94749cac62ed3741ff3e1cc5e8c' },
  { path: 'team/ayush-mendhe.webp', sha256: 'c1bfa7c5f2c1661500691c2d35ae1db1357a2f1fa99528a213e835021ba07dfc' },
  { path: 'team/joseph-olutayo.webp', sha256: '628624e750f9c4e916d130235339f8378945f516ed543876fe21864868035fd2' },
  { path: 'team/spatial_Barcelona.png', sha256: '0421ca9ceb2bef7f8b360813a5f36c0c725b34e15bd1da5400fe08e67a6f217b' },
  { path: 'team/spatial_Bayer_Leverkusen.png', sha256: '30bff5b12ab5cd763c651909bf28d7fb5d21b123fb5a9cc9dbe8aa408abeb602' },
  { path: 'team/spatial_Paris_Saint-Germain.png', sha256: '10914ca2b386cc3071af6668f3424577ed10649595ba0c05d73a3538d1bc480e' },
]);
const DEMO_DATA = new Map([
  [resolve(FRONTEND_ROOT, 'src/data/players.json'), '058c8885a893ebd80c92b47e4ae95a4484ad97e82bbe22738591b80be5d5c503'],
  [resolve(FRONTEND_ROOT, 'src/fixtures/syntheticFiveAttributes.json'), '9924967f2441f80524489d96f29058fa2f654dcb842b1d99854876d7e7540e14'],
]);
const FORBIDDEN_HASHES = new Set([
  // Exact original observations, including a renamed/binary copy.
  '9b6f0a5dd35782e5f6798e6521c5bab126466ca7b320dd7d54e8a38aad086b86',
]);
const DATA_EXTENSION = /\.(?:jsonl?|csv|tsv|parquet|arrow|feather|xlsx?|sqlite3?|db|ndjson)$/i;
const CODE_EXTENSION = new Set(['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.css', '.scss', '.sass', '.less', '.styl', '.html']);
const GENERATED_EXTENSION = new Set(['.html', '.js', '.mjs', '.css', '.map', '.woff', '.woff2']);
const within = (parent, path) => {
  const r = relative(parent, path);
  return r === '' || (!r.startsWith('..') && !isAbsolute(r));
};

async function checkedBytes(path, expected) {
  if ((await lstat(path)).isSymbolicLink() || await realpath(path) !== resolve(path)) denied(`symlink asset: ${path}`);
  const bytes = await readFile(path);
  if (digest(bytes) !== expected) denied(`reviewed public asset fingerprint changed: ${path}`);
  return bytes;
}

export async function validateDataImport(id) {
  const path = id.split('?')[0];
  if (!isAbsolute(path)) return; // Rollup virtual modules are not source files.
  const file = resolve(path);
  if (within(resolve(REPOSITORY_ROOT, 'data'), file) || within(resolve(FRONTEND_ROOT, 'src/dev'), file) || within(resolve(FRONTEND_ROOT, 'dev'), file)) {
    denied(`private/development source imported into production: ${file}`);
  }
  if (within(resolve(FRONTEND_ROOT, 'public'), file)) {
    const asset = PUBLIC_ASSETS.find((a) => resolve(FRONTEND_ROOT, 'public', a.path) === file);
    if (!asset) denied(`unreviewed public asset import: ${file}`);
    await checkedBytes(file, asset.sha256);
    return;
  }
  if (DATA_EXTENSION.test(file)) {
    // Dependency package manifests are code metadata, not a data admission path.
    if (file.split(/[\\/]/).includes('node_modules') && basename(file) === 'package.json') return;
    const expected = DEMO_DATA.get(file);
    if (!expected) denied(`unreviewed structured-data import: ${file}`);
    await checkedBytes(file, expected);
    return;
  }
  if (!CODE_EXTENSION.has(extname(file).toLowerCase()) && !['.woff', '.woff2'].includes(extname(file).toLowerCase())) {
    denied(`unreviewed source asset import: ${file}`);
  }
}

export function assertAdmittedOutput(name, input) {
  const bytes = typeof input === 'string' ? Buffer.from(input) : Buffer.from(input);
  const hash = digest(bytes);
  if (FORBIDDEN_HASHES.has(hash)) denied(`unauthorized observations payload in ${name}`);
  const publicAsset = PUBLIC_ASSETS.find((a) => a.path === name.replaceAll('\\', '/'));
  if (publicAsset) {
    if (hash !== publicAsset.sha256) denied(`changed static asset in ${name}`);
    return;
  }
  if (!GENERATED_EXTENSION.has(extname(name).toLowerCase())) denied(`unreviewed distributable file: ${name}`);
  if (['.woff', '.woff2'].includes(extname(name).toLowerCase())) {
    if (!['wOFF', 'wOF2'].includes(bytes.subarray(0, 4).toString('ascii'))) denied(`invalid font payload: ${name}`);
    return;
  }
  // These checks also cover JSON literals/strings in generated JS, renamed text
  // assets and source maps. Generic validator code is allowed; actual payloads
  // with real canonical season IDs or private envelope fields are not.
  const text = bytes.toString('utf8').replace(/\\u([a-f\d]{4})/gi, (_, h) => String.fromCharCode(parseInt(h, 16)))
    .replace(/\\([/"'])/g, '$1');
  if (/["'`][1-9]\d*:20\d\d\/20\d\d["'`]/.test(text) ||
      /["']?schema_version["']?\s*:\s*["'](?:soccer-provisional-observations\/|soccer-local-experimental-|private-five-attribute-)/.test(text) ||
      text.includes('403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd')) {
    denied(`real-player/private payload embedded in ${name}`);
  }
}

export async function verifyProductionDirectory(folder) {
  const files = [];
  async function visit(path) {
    for (const item of await readdir(path, { withFileTypes: true })) {
      const entry = resolve(path, item.name);
      if (item.isSymbolicLink()) denied(`symlink in production output: ${entry}`);
      if (item.isDirectory()) await visit(entry);
      else {
        const name = relative(folder, entry).replaceAll('\\', '/');
        assertAdmittedOutput(name, await readFile(entry));
        files.push(name);
      }
    }
  }
  await visit(resolve(folder));
  for (const asset of PUBLIC_ASSETS) if (!files.includes(asset.path)) denied(`missing reviewed static asset: ${asset.path}`);
  return files.sort();
}

export default function productionDataAdmission() {
  let config;
  const written = new Set();
  return {
    name: 'production-data-admission', apply: 'build', enforce: 'pre',
    config() { return { publicDir: false, build: { copyPublicDir: false } }; },
    configResolved(value) {
      config = value;
      if (config.publicDir || config.build.copyPublicDir !== false) denied('automatic public copying must remain disabled');
      config.logger.info('Production data admission: automatic public copying disabled; only the approved pinned final-ratings release, 98 pinned crests, 3 pinned heatmaps, 5 pinned About Us portraits, 691 pinned player portraits and 2 pinned demo/synthetic imports admitted. All other data remains denied.');
    },
    async load(id) { await validateDataImport(id); return null; },
    generateBundle: {
      order: 'post', sequential: true,
      async handler(_, bundle) {
        for (const asset of PUBLIC_ASSETS) this.emitFile({ type: 'asset', fileName: asset.path,
          source: await checkedBytes(resolve(FRONTEND_ROOT, 'public', asset.path), asset.sha256) });
        for (const [name, entry] of Object.entries(bundle)) assertAdmittedOutput(name, entry.type === 'chunk' ? entry.code : entry.source);
      },
    },
    writeBundle(options) { if (config.build.write !== false) written.add(resolve(options.dir ?? dirname(options.file))); },
    closeBundle: {
      order: 'post', sequential: true,
      async handler() { for (const folder of written) await verifyProductionDirectory(folder); },
    },
  };
}
