import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'

const BrandingContext = createContext()
const DEFAULTS = { brand_name: 'Nursery Analytics', brand_tagline: 'Early Years Intelligence', logo_url: null, icon_url: null }

export function BrandingProvider({ children }) {
  const [branding, setBranding] = useState(DEFAULTS)

  const apply = useCallback((b) => {
    setBranding(b)
    if (b.brand_name) document.title = b.brand_name
    // favicon
    let link = document.querySelector("link[rel~='icon']")
    if (b.icon_url) {
      if (!link) { link = document.createElement('link'); link.rel = 'icon'; document.head.appendChild(link) }
      link.href = b.icon_url
    }
  }, [])

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get('/settings/branding')
      apply({ ...DEFAULTS, ...data })
    } catch { /* keep defaults */ }
  }, [apply])

  useEffect(() => { refresh() }, [refresh])

  // first letter of the name for the fallback logo mark
  const letter = (branding.brand_name || 'N').trim().charAt(0).toUpperCase()

  return (
    <BrandingContext.Provider value={{ ...branding, letter, refresh, setBranding: apply }}>
      {children}
    </BrandingContext.Provider>
  )
}

export const useBranding = () => useContext(BrandingContext)
