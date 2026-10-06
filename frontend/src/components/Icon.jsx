const paths = {
  chat: 'M4 4h16v12H9l-5 4V4z',
  file: 'M6 3h8l4 4v14H6V3zm8 0v5h4M9 12h6m-6 4h6',
  history: 'M3 11a9 9 0 1 1 2 7M3 4v7h7m2-5v6l4 2',
  arrow: 'M5 12h14m-6-6 6 6-6 6',
  plus: 'M12 5v14M5 12h14',
  logout: 'M10 4H4v16h6m4-13 5 5-5 5m-6-5h11',
  upload: 'M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6',
  shield: 'M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6l-8-3zm-4 9 3 3 5-6',
}
export default function Icon({ name, size = 20 }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.chat}/></svg>
}
