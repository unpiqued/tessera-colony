// Inline SVG stand-ins for the SF Symbols the Swift app uses (24×24 grid, currentColor).
import { h } from './vdom.js';

const S = (d, extra = '') => `<path d="${d}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"${extra}/>`;
const F = d => `<path d="${d}" fill="currentColor"/>`;
const C = (cx, cy, r, fill) => `<circle cx="${cx}" cy="${cy}" r="${r}" ${fill ? 'fill="currentColor"' : 'fill="none" stroke="currentColor" stroke-width="2"'}/>`;

const ANT = F('M15.6 9.2c1.5 0 2.7 1.2 2.7 2.8s-1.2 2.8-2.7 2.8-2.7-1.3-2.7-2.8 1.2-2.8 2.7-2.8zm-5 1c1 0 1.8.8 1.8 1.8s-.8 1.8-1.8 1.8-1.8-.8-1.8-1.8.8-1.8 1.8-1.8zM5.4 9.4c1.4 0 2.6 1.1 2.6 2.6S6.8 14.6 5.4 14.6 2.8 13.5 2.8 12s1.2-2.6 2.6-2.6z')
  + S('M10.6 10.2 9 6.5 6.5 5.5M10.6 13.8 9 17.5l-2.5 1M12 10.6l2-4.1 2.8-1.3M12 13.4l2 4.1 2.8 1.3M8.5 11.2 7.5 8M8.5 12.8 7.5 16M18.2 11l2.6-2.2M18.2 13l2.6 2.2', ' stroke-width="1.5"');

const ICONS = {
  'xmark': S('M6 6l12 12M18 6 6 18'),
  'xmark.circle.fill': C(12, 12, 10, true) + `<path d="M8.5 8.5l7 7M15.5 8.5l-7 7" stroke="var(--icon-ink,#2A1C12)" stroke-width="2.2" stroke-linecap="round"/>`,
  'ellipsis.circle.fill': C(12, 12, 10.5, true) + `<g fill="var(--icon-ink,#4A3A2C)"><circle cx="7.5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="16.5" cy="12" r="1.6"/></g>`,
  'questionmark.circle': C(12, 12, 9.5) + S('M9.5 9.3a2.6 2.6 0 0 1 5 .9c0 1.7-2.5 2.2-2.5 3.8') + `<circle cx="12" cy="17.2" r="1.2" fill="currentColor"/>`,
  'questionmark': S('M8.8 8.6a3.3 3.3 0 0 1 6.4 1.1c0 2.2-3.2 2.8-3.2 4.9') + `<circle cx="12" cy="18.6" r="1.4" fill="currentColor"/>`,
  'arrow.counterclockwise': S('M4.5 12a7.5 7.5 0 1 0 2.3-5.4M4.5 4.5v4h4'),
  'ant': ANT, 'ant.fill': ANT,
  'speaker.wave.2': F('M4 9.5h3l4.5-4v13L7 14.5H4z') + S('M15 9a4 4 0 0 1 0 6M17.6 6.5a7.5 7.5 0 0 1 0 11'),
  'speaker.wave.2.fill': F('M4 9.5h3l4.5-4v13L7 14.5H4z') + S('M15 9a4 4 0 0 1 0 6M17.6 6.5a7.5 7.5 0 0 1 0 11'),
  'speaker.wave.3': F('M3 9.5h3l4.5-4v13L6 14.5H3z') + S('M13.5 9.3a3.6 3.6 0 0 1 0 5.4M16 7a6.8 6.8 0 0 1 0 10M18.6 4.6a10 10 0 0 1 0 14.8'),
  'point.topleft.down.curvedto.point.bottomright.up': C(5, 5, 2.2, true) + C(19, 19, 2.2, true) + S('M5 7.5c0 7 14 2 14 9'),
  'paintpalette': S('M12 3a9 9 0 1 0 0 18c1.5 0 2-1 2-2s-1-1.6-1-2.6 1-1.4 2-1.4h2.5A3.5 3.5 0 0 0 21 11.5C21 6.8 17 3 12 3z') + `<g fill="currentColor"><circle cx="7.5" cy="11" r="1.3"/><circle cx="10" cy="7.3" r="1.3"/><circle cx="14.5" cy="7.3" r="1.3"/></g>`,
  'paintpalette.fill': F('M12 3a9 9 0 1 0 0 18c1.5 0 2-1 2-2s-1-1.6-1-2.6 1-1.4 2-1.4h2.5A3.5 3.5 0 0 0 21 11.5C21 6.8 17 3 12 3z') + `<g fill="var(--icon-ink,#2A1C12)"><circle cx="7.5" cy="11" r="1.4"/><circle cx="10" cy="7.3" r="1.4"/><circle cx="14.5" cy="7.3" r="1.4"/></g>`,
  'house': S('M4 11 12 4l8 7M6 9.5V20h12V9.5M10 20v-5h4v5'),
  'plus': S('M12 5v14M5 12h14'),
  'arrow.uturn.backward': S('M9 5 4.5 9.5 9 14M4.5 9.5H15a4.5 4.5 0 0 1 0 9h-3'),
  'arrow.uturn.backward.circle': C(12, 12, 9.5) + S('M10 8l-3 3 3 3M7 11h6a2.6 2.6 0 0 1 0 5.2h-1.5'),
  'arrow.uturn.down': S('M8 4v7a4 4 0 0 0 8 0V9', ' stroke-width="3"') + S('M12.5 12.5 16 16l3.5-3.5', ' stroke-width="3" transform="translate(0,-4)"'),
  'lightbulb': S('M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z'),
  'lightbulb.fill': F('M12 2.5a6.5 6.5 0 0 0-3.8 11.8c.6.4.9 1 .9 1.7h5.8c0-.7.3-1.3.9-1.7A6.5 6.5 0 0 0 12 2.5z') + S('M9.2 18.5h5.6M10.2 21h3.6'),
  'lightbulb.slash': S('M9 18h6M10 21h4M8.7 5.5A6 6 0 0 1 17.5 12M8.5 13.9c.6.5 1 1.2 1 2.1h5M3 3l18 18'),
  'hourglass': S('M7 3h10M7 21h10M8 3c0 5 8 5 8 9s-8 4-8 9M16 3c0 5-8 5-8 9s8 4 8 9'),
  'tortoise.fill': F('M4 14c0-3.9 3.1-7 7-7s7 3.1 7 7H4z') + F('M18 12.5c1.2-.9 2.4-1.2 3.3-.6.4 1-.6 1.9-2.3 2.1H18z') + S('M6 14v3M9.5 14v3M13 14v3M16 14v3'),
  'hare.fill': F('M6 16c0-3.3 3.1-6 7-6 2 0 3.3.6 4.4 1.6L20 11c1 0 1.5 1 1 1.8l-2 2.1c-.6 1.5-2.4 2.6-4.5 2.6H7.5C6.7 17.5 6 16.9 6 16z') + S('M16.5 11 15 5.5M18.3 11.5 19 5.8M7 15l-3 1.5') ,
  'eye.fill': F('M12 5C6.5 5 3 12 3 12s3.5 7 9 7 9-7 9-7-3.5-7-9-7z') + `<circle cx="12" cy="12" r="3.2" fill="var(--icon-ink,#2A1C12)"/>`,
  'eye.slash': S('M3 12s3.5-7 9-7c1.6 0 3 .5 4.3 1.3M21 12s-3.5 7-9 7c-1.6 0-3-.5-4.3-1.3M10 9.8a3.2 3.2 0 0 1 4.3 4.3M3 3l18 18'),
  'binoculars': S('M5 8l1.5-4h3L10 8M14 8l.5-4h3L19 8') + C(6.8, 15, 4) + C(17.2, 15, 4) + S('M10.5 13.5h3'),
  'sparkles': F('M10 2.5l1.6 4.9 4.9 1.6-4.9 1.6L10 15.5l-1.6-4.9L3.5 9l4.9-1.6zM18 13l.9 2.6 2.6.9-2.6.9L18 20l-.9-2.6-2.6-.9 2.6-.9z'),
  'exclamationmark.triangle.fill': F('M12 3 1.8 20.5h20.4z') + `<path d="M12 9.5v5" stroke="var(--icon-ink,#2A1C12)" stroke-width="2.2" stroke-linecap="round"/><circle cx="12" cy="17.4" r="1.3" fill="var(--icon-ink,#2A1C12)"/>`,
  'plus.square.dashed': S('M12 8.5v7M8.5 12h7') + `<rect x="3.5" y="3.5" width="17" height="17" rx="3" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="3.5 2.5"/>`,
  'arrow.down.to.line': S('M12 4v11M7.5 10.5 12 15l4.5-4.5M5 20h14'),
  'star': S('M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1 5.9L12 17l-5.2 2.7 1-5.9-4.3-4.1 5.9-.8z'),
  'star.fill': F('M12 2.8l2.8 5.8 6.4.9-4.6 4.4 1.1 6.3L12 17.2l-5.7 3 1.1-6.3-4.6-4.4 6.4-.9z'),
  'flame.fill': F('M12 2.5c.7 3.2 5.5 5.6 5.5 11a5.5 5.5 0 0 1-11 0c0-2.6 1.3-4.2 2.6-5.4.2 1.7.9 2.8 2 3.4-.3-3.6-.1-6.4.9-9z'),
  'stopwatch.fill': F('M12 6a8 8 0 1 0 0 16 8 8 0 0 0 0-16z') + `<path d="M12 9.5V14" stroke="var(--icon-ink,#2A1C12)" stroke-width="2.2" stroke-linecap="round"/>` + S('M9.5 2.5h5M12 2.5V6'),
  'trophy': S('M7 4h10v5a5 5 0 0 1-10 0zM7 6H4.5a2.5 2.5 0 0 0 2.6 3.6M17 6h2.5a2.5 2.5 0 0 1-2.6 3.6M12 14v3.5M8.5 20.5h7M9.5 17.5h5v3h-5z'),
  'trophy.fill': F('M7 3.5h10v5.5a5 5 0 0 1-10 0z') + S('M7 6H4.5a2.5 2.5 0 0 0 2.6 3.6M17 6h2.5a2.5 2.5 0 0 1-2.6 3.6M12 14v3.5M8 20.5h8') + F('M9.3 17h5.4v3.5H9.3z'),
  'arrow.up.circle': C(12, 12, 9.5) + S('M12 16.5v-9M8 11.5l4-4 4 4'),
  'arrow.up.circle.fill': C(12, 12, 10, true) + `<path d="M12 16.5v-9M8 11.5l4-4 4 4" fill="none" stroke="var(--icon-ink,#2A1C12)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>`,
  'person.2.fill': F('M9 4a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7zM2.5 19c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6v1h-13zM16.5 5.5a3 3 0 1 1 0 6 3 3 0 0 1 0-6zM17 13c2.9.2 4.8 2.4 4.8 5.3V20h-4.3v-1c0-2.4-.9-4.5-2.5-5.8.6-.1 1.3-.2 2-.2z'),
  'chevron.right': S('M9 5l7 7-7 7', ' stroke-width="2.6"'),
  'gearshape': S('M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z') + S('M19.4 13.4a7.6 7.6 0 0 0 0-2.8l2-1.6-2-3.4-2.4.9a7.4 7.4 0 0 0-2.4-1.4L14.2 2.5h-4l-.4 2.6a7.4 7.4 0 0 0-2.4 1.4L5 5.6 3 9l2 1.6a7.6 7.6 0 0 0 0 2.8L3 15l2 3.4 2.4-.9a7.4 7.4 0 0 0 2.4 1.4l.4 2.6h4l.4-2.6a7.4 7.4 0 0 0 2.4-1.4l2.4.9 2-3.4z'),
  'lock.fill': F('M6 10.5h12a1.5 1.5 0 0 1 1.5 1.5v7.5A1.5 1.5 0 0 1 18 21H6a1.5 1.5 0 0 1-1.5-1.5V12A1.5 1.5 0 0 1 6 10.5z') + S('M8 10.5V8a4 4 0 0 1 8 0v2.5'),
  'checkmark.seal.fill': F('M12 2l2.4 1.8 3-.2.9 2.9 2.5 1.7-1 2.8 1 2.8-2.5 1.7-.9 2.9-3-.2L12 22l-2.4-1.8-3 .2-.9-2.9-2.5-1.7 1-2.8-1-2.8 2.5-1.7.9-2.9 3 .2z') + `<path d="M8.3 12.2l2.5 2.5 5-5" fill="none" stroke="var(--icon-ink,#2A1C12)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>`,
  'trash': S('M4.5 6.5h15M9.5 6.5V4h5v2.5M6.5 6.5l1 13.5h9l1-13.5M10.3 10.5v6M13.7 10.5v6'),
  'magnifyingglass': C(10.5, 10.5, 6) + S('M15 15l5.5 5.5'),
  'square.grid.2x2': S('M4 4h6.5v6.5H4zM13.5 4H20v6.5h-6.5zM4 13.5h6.5V20H4zM13.5 13.5H20V20h-6.5z'),
  'wand.and.stars': S('M4 20 15 9M13 7l4 4') + F('M18 2.5l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8zM8.5 3l.6 1.5 1.5.6-1.5.6-.6 1.5-.6-1.5L6.4 5l1.5-.6zM19.5 12.5l.6 1.5 1.5.6-1.5.6-.6 1.5-.6-1.5-1.5-.6 1.5-.6z'),
  'photo': S('M4 5h16v14H4z') + S('M4 16l5-5 4 4 2.5-2.5L20 17') + C(15.5, 9, 1.6, true),
  'photo.on.rectangle': S('M7 7h14v12H7zM3 4h14') + S('M7 16l4-4 3 3 2-2 5 4'),
  'photo.on.rectangle.angled': S('M7 7h14v12H7zM3.5 15.5 2.5 6l13-1.8') + S('M7 16l4-4 3 3 2-2 5 4'),
  'info.circle.fill': C(12, 12, 10, true) + `<path d="M12 11v6" stroke="var(--icon-ink,#2A1C12)" stroke-width="2.3" stroke-linecap="round"/><circle cx="12" cy="7.6" r="1.4" fill="var(--icon-ink,#2A1C12)"/>`,
  'leaf.fill': F('M20.5 3.5C11 3.5 4.5 7.5 4.5 14c0 1.6.4 3 1.1 4.2C8 12.8 12 10 15.5 8.5 11.5 11 8.3 14.8 6.6 19.4 7.8 20.4 9.4 21 11 21c6.6 0 9.5-7.7 9.5-17.5z'),
  'book.fill': F('M3 5.5C5.6 4.3 8.6 4.3 11.2 5.9V20c-2.6-1.4-5.6-1.4-8.2-.3zM12.8 5.9C15.4 4.3 18.4 4.3 21 5.5v14.2c-2.6-1.1-5.6-1.1-8.2.3z'),
  'building.columns.fill': F('M12 2.5 21 7v2H3V7zM4 19h16v2.5H4zM5.5 10.5h2.5V17.5H5.5zM10.75 10.5h2.5V17.5h-2.5zM16 10.5h2.5V17.5H16z'),
  'snowflake': S('M12 2.5v19M3.8 7.2l16.4 9.6M3.8 16.8l16.4-9.6M9.5 4.5 12 7l2.5-2.5M9.5 19.5 12 17l2.5 2.5M4.3 10.9l3.4-.9-.9-3.4M19.7 13.1l-3.4.9.9 3.4M6.8 17.4l.9-3.4-3.4-.9M17.2 6.6l-.9 3.4 3.4.9', ' stroke-width="1.6"'),
  'hand.raised.slash': S('M8.5 12V5.5a1.5 1.5 0 0 1 3 0V11M11.5 5V3.8a1.5 1.5 0 0 1 3 0V11M14.5 6.5a1.5 1.5 0 0 1 3 0v7c0 4-2.7 7-6.5 7-2.5 0-4.2-1.4-5.4-3.6L4 13.2a1.4 1.4 0 0 1 2.3-1.5L8.5 14M3 3l18 18'),
  'circle.lefthalf.filled': C(12, 12, 9) + F('M12 3a9 9 0 0 0 0 18z'),
  'square': `<rect x="3.5" y="3.5" width="17" height="17" rx="3.5" fill="none" stroke="currentColor" stroke-width="2"/>`,
  'checkmark.square.fill': `<rect x="3" y="3" width="18" height="18" rx="4" fill="currentColor"/><path d="M7.5 12.3l3 3 6-6.3" fill="none" stroke="var(--icon-ink,#2A1C12)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>`,
  'circle': C(12, 12, 9),
  'largecircle.fill.circle': C(12, 12, 9.5) + C(12, 12, 5, true),
  'checkmark.circle.fill': C(12, 12, 10, true) + `<path d="M7.5 12.3l3 3 6-6.3" fill="none" stroke="var(--icon-ink,#2A1C12)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>`,
  'xmark.octagon.fill': F('M8.3 2.5h7.4l5.8 5.8v7.4l-5.8 5.8H8.3l-5.8-5.8V8.3z') + `<path d="M9 9l6 6M15 9l-6 6" stroke="var(--icon-ink,#2A1C12)" stroke-width="2.2" stroke-linecap="round"/>`,
  'square.stack.fill': F('M6 8h12a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-9a2 2 0 0 1 2-2z') + S('M6.5 5h11M8.5 2.5h7'),
  'square.grid.3x3.fill': F('M3 3h5v5H3zM9.5 3h5v5h-5zM16 3h5v5h-5zM3 9.5h5v5H3zM9.5 9.5h5v5h-5zM16 9.5h5v5h-5zM3 16h5v5H3zM9.5 16h5v5h-5zM16 16h5v5h-5z'),
  'slider.horizontal.3': S('M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1') + C(15, 6, 2) + C(9, 12, 2) + C(17, 18, 2),
  'hand.pinch.fill': F('M9 3a1.6 1.6 0 0 1 1.6 1.6v6.6l1-.2V8a1.6 1.6 0 0 1 3.2 0v4l.7-.1a1.6 1.6 0 0 1 3.2.6v2.8c0 3.6-2.6 6.2-6.4 6.2-2.2 0-3.8-1-5-3l-3-5a1.5 1.5 0 0 1 2.5-1.6l.6.9V4.6A1.6 1.6 0 0 1 9 3z'),
  'arrow.up.right': S('M6 18 18 6M8.5 6H18v9.5'),
  'line.diagonal': S('M5 19 19 5'),
  'scribble': S('M3 15c3-6 5-8 6-6s-3 7-1 8 5-9 7-8-2 7 0 7 3-3 5-5'),
  'square.dashed': `<rect x="3.5" y="3.5" width="17" height="17" rx="3" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="3.5 2.5"/>`,
  'shuffle': S('M3 7h3.5c4 0 6 10 10 10H21M3 17h3.5c1.6 0 2.8-1.6 3.8-3.6M13.7 9.6C14.7 8 15.6 7 17 7h4M18.5 4.5 21 7l-2.5 2.5M18.5 14.5 21 17l-2.5 2.5'),
  'dice': `<rect x="3.5" y="3.5" width="17" height="17" rx="3.5" fill="none" stroke="currentColor" stroke-width="2"/><g fill="currentColor"><circle cx="8.3" cy="8.3" r="1.5"/><circle cx="15.7" cy="8.3" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="8.3" cy="15.7" r="1.5"/><circle cx="15.7" cy="15.7" r="1.5"/></g>`,
  'checkmark': S('M5 12.5l4.5 4.5L19 7.5', ' stroke-width="2.6"'),
  'house.fill': F('M12 3.5 3 11v1.5h2V21h5v-5.5h4V21h5v-8.5h2V11z'),
  'lock.open.fill': F('M6 10.5h12a1.5 1.5 0 0 1 1.5 1.5v7.5A1.5 1.5 0 0 1 18 21H6a1.5 1.5 0 0 1-1.5-1.5V12A1.5 1.5 0 0 1 6 10.5z') + S('M8 10.5V7.5a4 4 0 0 1 7.6-1.7'),
  'doc.on.doc': S('M8.5 7.5V5A1.5 1.5 0 0 1 10 3.5h8A1.5 1.5 0 0 1 19.5 5v10a1.5 1.5 0 0 1-1.5 1.5h-2.5M6 7.5h8A1.5 1.5 0 0 1 15.5 9v10A1.5 1.5 0 0 1 14 20.5H6A1.5 1.5 0 0 1 4.5 19V9A1.5 1.5 0 0 1 6 7.5z'),
  'square.and.arrow.down': S('M12 3.5v11M7.5 10 12 14.5 16.5 10M8 7.5H6A1.5 1.5 0 0 0 4.5 9v10A1.5 1.5 0 0 0 6 20.5h12a1.5 1.5 0 0 0 1.5-1.5V9A1.5 1.5 0 0 0 18 7.5h-2'),
};

/** An icon as a vnode. `name` is the SF Symbol name used by the Swift code. */
export function icon(name, size = 18, cls = '') {
  const body = ICONS[name] || ICONS['questionmark'];
  return h('span', {
    class: 'icon ' + cls,
    'aria-hidden': 'true',
    style: { width: size + 'px', height: size + 'px' },
    html: `<svg viewBox="0 0 24 24" width="${size}" height="${size}">${body}</svg>`,
  });
}

export function hasIcon(name) { return name in ICONS; }
