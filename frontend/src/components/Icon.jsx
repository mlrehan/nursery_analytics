// Minimal inline line-icon set keyed by the module.icon values from the backend.
const paths = {
  gauge: 'M12 14a2 2 0 100-4 2 2 0 000 4zm0-12a10 10 0 100 20 10 10 0 000-20zm0 0v4m6.36 1.64l-2.83 2.83',
  users: 'M17 20v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 10a4 4 0 100-8 4 4 0 000 8zm14 10v-2a4 4 0 00-3-3.87M16 2.13a4 4 0 010 7.75',
  pound: 'M18 7c0-2.21-2-4-4.5-4S9 4.79 9 7c0 4-2 5-2 5h11M7 12h7M6 19h12',
  badge: 'M12 2l2.4 4.9 5.4.8-3.9 3.8.9 5.4L12 14.8 7.2 17l.9-5.4L4.2 7.7l5.4-.8L12 2z',
  shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z',
  sparkles: 'M12 3v6m0 6v6m9-9h-6m-6 0H3m13.5-6.5L14 7m-4 4l-2.5 2.5m9 0L14 11m-4-4L7.5 4.5',
  clipboard: 'M9 4h6a1 1 0 011 1v1h2a1 1 0 011 1v13a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h2V5a1 1 0 011-1z',
  chat: 'M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z',
  apple: 'M12 7c0-2 1.5-4 4-4 0 2-1.5 4-4 4zm0 0c-2.5 0-5 1.5-5 5s2 8 5 8 5-4 5-8-2.5-5-5-5z',
  building: 'M3 21h18M5 21V5a1 1 0 011-1h6a1 1 0 011 1v16M13 9h6a1 1 0 011 1v11M8 8h2m-2 4h2m-2 4h2',
  trending: 'M3 17l6-6 4 4 8-8M21 7v6h-6',
  alert: 'M12 9v4m0 4h.01M10.3 3.3L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.3a2 2 0 00-3.4 0z',
  cog: 'M12 15a3 3 0 100-6 3 3 0 000 6zm7.4-3a7.4 7.4 0 00-.1-1.2l2-1.6-2-3.4-2.4 1a7.3 7.3 0 00-2-1.2L17.5 2h-4l-.4 2.4a7.3 7.3 0 00-2 1.2l-2.4-1-2 3.4 2 1.6a7.4 7.4 0 000 2.4l-2 1.6 2 3.4 2.4-1a7.3 7.3 0 002 1.2l.4 2.4h4l.4-2.4a7.3 7.3 0 002-1.2l2.4 1 2-3.4-2-1.6c.06-.4.1-.8.1-1.2z',
  phone: 'M7 4h10a1 1 0 011 1v14a1 1 0 01-1 1H7a1 1 0 01-1-1V5a1 1 0 011-1zm4 14h2',
  cpu: 'M9 9h6v6H9zM4 9h1m-1 6h1m15-6h1m-1 6h1M9 4v1m6-1v1M9 20v-1m6 1v-1M6 6h12v12H6z',
}

export default function Icon({ name, className = 'w-5 h-5' }) {
  const d = paths[name] || paths.gauge
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  )
}
