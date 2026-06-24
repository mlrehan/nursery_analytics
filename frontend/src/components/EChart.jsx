import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

/** Thin, theme-aware wrapper around Apache ECharts with optional click events. */
export default function EChart({ option, height = 300, className = '', onEvents }) {
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
    const c = chart.current
    if (!c || !option) return
    c.setOption(option, true)
    if (onEvents) {
      Object.entries(onEvents).forEach(([evt, fn]) => {
        c.off(evt)
        c.on(evt, fn)
      })
    }
  }, [option, onEvents])

  return <div ref={ref} style={{ height, width: '100%' }} className={className} />
}
