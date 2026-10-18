// HowToPlayView (Overlays.swift), with the wording adapted where the browser differs from the iPad.
import { h } from './vdom.js';
import { icon } from './icons.js';
import { sheet } from './components.js';
import { swatchURL } from './swatch.js';
import { builtInPalette, paletteName } from './compat.js';

const RULES = [
  ['ant.fill', 'Send a team', 'Tap the team at the front of any tunnel. Its ants leave the hill and claim every tile of their colour they can reach, nearest first, up to the team’s number. Each tap sends the next team in that tunnel — as long as a slot is open.'],
  ['square.stack.fill', 'Slots', 'Every team you send takes a slot. The number on a working team counts down as its ants pick up tiles; when it reaches zero the slot opens again. Several teams can work at once, one per slot, and you can’t send more than the open slots allow.'],
  ['square.grid.3x3.fill', 'Reachable tiles', 'Ants walk only on open ground. A tile can be taken when it touches open ground connected to the hill. A team can tunnel through its own colour.'],
  ['hourglass', 'Waiting teams', 'To make a team wait, just send it. If it can’t reach all its tiles yet, it keeps its slot and waits, resuming by itself as its colour is uncovered. Waiting teams are the ones that can block you, so scout first if you’re unsure.'],
  ['exclamationmark.triangle.fill', 'Blocked?', 'If every slot holds a waiting team, nothing can be sent. Undo is free and unlimited. You can also add a slot, or tap a waiting team to return it to the front of its tunnel and open its slot.'],
  ['eye.fill', 'Scout', 'Press and hold a team (or right-click it with a mouse) to preview exactly which tiles it would take and whether it would have to wait.'],
  ['lightbulb.fill', 'Hints', 'A hint suggests the next team, or tells you how many moves to undo to get back to a winning line.'],
  ['slider.horizontal.3', 'Difficulty', 'Choose Gentle, Classic or Expert at the top of Home (or on a mosaic’s start card). Each mosaic shows its slots and a measured rating from Relaxed to Fiendish, with how often careless tapping wins. The Show filter keeps only Easy, Medium, Hard or Fiendish mosaics.'],
  ['flame.fill', 'Packs and your collection', '193 mosaics in twenty-five packs, grouped into themes: the main Mosaics, Seasons (Halloween, Winter — the one in season wears a badge), Nature (Garden, Wild Wonders, Natural History), Art (Gallery, World Art, World Craft), Literature (Epics & Legends, Fairy Tales & Fables, Children’s Classics, Shakespeare, Adventure Classics, Gothic & Mystery, Great Novels), History (Ancient World, Voyages, Modern Moments, Inventions & Firsts), Sky & Science (Sky & Science, Probes & Telescopes, Geometry & Illusions), and the Challenge and Master packs. When a pack opens, its first three mosaics are found; each one you finish finds another (the rest show as ?). Finishing earns stars — one for Gentle, two for Classic, three for Expert — and a flame for Expert with a harder option. The Status filter on Home finds what to explore next or what to play harder. On the hardest mosaics, sending whatever can finish now isn’t enough — scout, plan ahead and use undo.'],
  ['eye.slash', 'Harder options', 'On the start card: Hidden queue, No scouting, No hints, 3 undos, No assists and No colour twice. Each one raises your score multiplier; none makes a mosaic impossible.'],
  ['trophy.fill', 'High scores', 'Score = tiles × difficulty (Gentle ×0.5, Classic ×1, Expert ×1.5) × harder options, minus 5 per undo, 25 per hint and 25 per assist. Make a mosaic’s top 5 and type your name on the finish card. Home → High scores shows every table.'],
  ['xmark', 'Leaving a game', 'The X in the top-left corner goes straight back to Home. The game is saved — Resume picks it up.'],
  ['person.2.fill', 'Two players', 'Home → Two players (the big button at the top). The winner can put their name on the mosaic’s two-player high-score table. Race on two copies of a mosaic (split screen) or share one board with two ant hills. Choose Front team only or Reach 3 (jumping the queue costs 3 points a place), any colour or no colour twice in a row, and slot upkeep or a flat slot cost. Score = tiles your ants carry home minus penalties.'],
  ['point.topleft.down.curvedto.point.bottomright.up', 'Ant paths', 'Menu → Ant paths changes how newly launched ants walk to their tiles: Direct, Natural, Curious (some stop to sniff), Wall-hugger, Scout trail (a fading trail the team follows), Random per team (the default — each team picks one of the styles when it is sent) or Random per ant. Ants carrying tiles come home in the middle lane.'],
  ['speaker.wave.2.fill', 'Sound', 'Wood-and-clay sounds for your moves, bells and glass for goals (a team done, a colour lifted, every quarter home, the finish, a new best, an unlock), and a clink for every tile. Each set has its own switch in Settings. Browsers only play sound after your first tap.'],
  ['tortoise.fill', 'Ant speed', 'Drag the Ant speed slider (0.1× to 16×) to watch the colony crawl slowly or hurry. Ants already walking just change pace. The setting is remembered.'],
  ['paintpalette', 'Ground colour', 'Menu → Ground colour… sets the colour behind the mosaic: pick a preset or any colour.'],
  ['hand.pinch.fill', 'Zoom', 'Pinch the board (or ctrl + scroll) to watch the ants up close; drag to pan; double-tap to reset.'],
  ['photo.on.rectangle', 'Your photos', 'Turn any photo into a mosaic from the home screen. White and near-white areas become open ground, so no moves are wasted on background.'],
  ['paintpalette.fill', 'Colours', 'Tiles are shaded, but shading never changes a tile’s colour family. Team pieces are made of the same tiles they collect; each ant is painted the colour of the tile it is fetching.'],
];

export function howToSheet(onDone) {
  const pal = builtInPalette();
  return sheet('How to play', onDone, [
    h('div', { class: 'rules' }, RULES.map(([ic, title, text]) => h('div', { class: 'rule', key: title },
      h('span', { class: 'brass', style: { width: '34px', display: 'flex', justifyContent: 'center' } }, icon(ic, 24)),
      h('div', { class: 'col', style: { gap: '4px' } }, h('div', { class: 'title' }, title), h('div', { class: 'dim', style: { fontSize: '15px', lineHeight: '1.45' } }, text))))),
    h('div', { class: 'title', style: { fontSize: '19px', marginTop: '6px' } }, 'Colour families in the built-in mosaics'),
    h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: '10px' } },
      pal.tones.map((_, f) => h('div', { key: 'f' + f, class: 'col', style: { gap: '4px' } },
        h('div', { style: { height: '36px', borderRadius: '8px', backgroundImage: `url(${swatchURL(pal, f, 12, 200, 36)})`, backgroundSize: '200px 36px' } }),
        h('div', { class: 'dim', style: { fontSize: '13px', fontWeight: 700 } }, paletteName(pal, f))))),
  ], { key: 'howto', large: true });
}
