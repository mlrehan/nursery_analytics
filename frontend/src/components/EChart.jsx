import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

/** Thin, theme-aware wrapper around Apache ECharts. */
export default function EChart({ option, height = 300, className = '' }) {
  const ref = useRef(null)
  const chart = useRef(null)

  useEffect(() => {
    if (!ref.current) return
    chart.current = echarts.init(ref.current, null, { renderer: 'canvas' })
    const ro = new ResizeObserver(() => chart.current?.resize())
    ro.observe(ref.current)
    return () => { ro.disconnect(); chart.current?.dispose(); chart.current = null }
  }, [])

  useEffect(() => {
    if (chart.current && option) {
      chart.current.setOption(option, true)
    }
  }, [option])

  return <div ref={ref} style={{ height, width: '100%' }} className={className} />
}
