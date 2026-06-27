/** Slim, prominent banner shown while the deployment is in demo mode, so viewers
 *  never mistake synthetic data for a real nursery's. Admin toggles it off in
 *  Branding & Settings once real data is loaded. */
export default function DemoBanner({ brand = 'Falgoon', show = true }) {
  if (!show) return null
  return (
    <div className="no-print w-full text-center text-[12.5px] font-semibold px-4 py-1.5 text-white"
      style={{ background: 'linear-gradient(90deg,#b45309,#d97706,#b45309)' }}>
      <span className="inline-flex items-center gap-2">
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
          <path d="M12 9v4m0 4h.01M10.3 3.3L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.3a2 2 0 00-3.4 0z" /></svg>
        Fictional data — this demo uses synthetic data to illustrate {brand}'s analytics capabilities.
      </span>
    </div>
  )
}
