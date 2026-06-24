import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

const FilterContext = createContext()

export function FilterProvider({ children }) {
  const [sites, setSites] = useState([])
  const [canPickSite, setCanPickSite] = useState(false)
  const [periods, setPeriods] = useState([
    { value: 7, label: '7 days' }, { value: 30, label: '30 days' },
    { value: 90, label: '90 days' }, { value: 365, label: '12 months' },
  ])
  const [siteId, setSiteId] = useState(null)   // null = all sites
  const [days, setDays] = useState(90)

  useEffect(() => {
    api.get('/dashboards/filters').then(({ data }) => {
      setSites(data.sites || [])
      setCanPickSite(!!data.can_pick_site)
      if (data.periods?.length) setPeriods(data.periods)
      if (data.default_period) setDays(data.default_period)
    }).catch(() => {})
  }, [])

  const value = useMemo(() => ({
    sites, canPickSite, periods, siteId, days, setSiteId, setDays,
    siteName: sites.find((s) => s.id === siteId)?.name,
  }), [sites, canPickSite, periods, siteId, days])

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>
}

export const useFilters = () => useContext(FilterContext)
