// Builds Apache ECharts option objects from the backend payload contract.
// Every chart in the app is rendered by ECharts (mandatory).
import * as echarts from 'echarts'

const PALETTE = ['#3b82f6', '#34d399', '#a78bfa', '#fbbf24', '#22d3ee', '#fb923c', '#ec4899', '#14b8a6']
const ACCENT_HEX = {
  blue: '#3b82f6', emerald: '#10b981', violet: '#8b5cf6',
  amber: '#f59e0b', cyan: '#06b6d4', orange: '#f97316',
}

function theme(dark) {
  return {
    text: dark ? '#9fb0cc' : '#475569',
    axis: dark ? '#26314e' : '#e2e8f0',
    split: dark ? 'rgba(38,49,78,0.6)' : '#eef2f7',
    tooltipBg: dark ? '#0f1626' : '#ffffff',
    tooltipBorder: dark ? '#26314e' : '#e2e8f0',
    tooltipText: dark ? '#e6ecf7' : '#0f172a',
  }
}

const baseGrid = { left: 8, right: 16, top: 36, bottom: 28, containLabel: true }

function tooltip(t, trigger = 'axis') {
  return {
    trigger,
    backgroundColor: t.tooltipBg,
    borderColor: t.tooltipBorder,
    borderWidth: 1,
    textStyle: { color: t.tooltipText, fontSize: 12 },
    extraCssText: 'border-radius:10px;box-shadow:0 8px 24px -8px rgba(0,0,0,.35);',
  }
}
function legend(t, top = 'top') {
  return { top, right: 0, textStyle: { color: t.text }, icon: 'roundRect', itemWidth: 10, itemHeight: 10, itemGap: 14 }
}
function axisLine(t, showSplit = true) {
  return {
    axisLine: { lineStyle: { color: t.axis } },
    axisTick: { show: false },
    axisLabel: { color: t.text, fontSize: 11 },
    splitLine: showSplit ? { lineStyle: { color: t.split } } : { show: false },
  }
}
function gradient(hex) {
  return new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: hex + '55' },
    { offset: 1, color: hex + '02' },
  ])
}

/** Tiny KPI sparkline (no axes). */
export function buildSparkline(data, accent = 'blue') {
  const hex = ACCENT_HEX[accent] || ACCENT_HEX.blue
  return {
    grid: { left: 0, right: 0, top: 4, bottom: 0 },
    xAxis: { type: 'category', show: false, boundaryGap: false, data: data.map((_, i) => i) },
    yAxis: { type: 'value', show: false, scale: true },
    tooltip: { show: false },
    series: [{
      type: 'line', data, smooth: true, showSymbol: false,
      lineStyle: { width: 2, color: hex }, areaStyle: { color: gradient(hex) },
    }],
  }
}

export function buildOption(vizType, payload, dark) {
  const t = theme(dark)
  if (!payload) return {}

  switch (vizType) {
    case 'line': {
      return {
        color: PALETTE,
        tooltip: tooltip(t),
        legend: legend(t),
        grid: baseGrid,
        xAxis: { type: 'category', boundaryGap: false, data: payload.x || [], ...axisLine(t, false) },
        yAxis: { type: 'value', ...axisLine(t) },
        series: (payload.series || []).map((s, i) => ({
          name: s.name, type: 'line', smooth: true, showSymbol: false, data: s.data, connectNulls: false,
          lineStyle: i === 1 ? { width: 2, type: 'dashed' } : { width: 2.5 },
          areaStyle: i === 0 ? { color: gradient(PALETTE[0]) } : undefined,
        })),
      }
    }
    case 'bar':
    case 'stacked_bar': {
      const stacked = vizType === 'stacked_bar' || payload.stack
      return {
        color: PALETTE,
        tooltip: tooltip(t),
        legend: legend(t),
        grid: baseGrid,
        xAxis: { type: 'category', data: payload.categories || [], ...axisLine(t, false) },
        yAxis: { type: 'value', ...axisLine(t) },
        series: (payload.series || []).map((s) => ({
          name: s.name, type: 'bar', data: s.data, stack: stacked ? 'total' : undefined,
          barMaxWidth: 36, itemStyle: { borderRadius: stacked ? 0 : [5, 5, 0, 0] },
          emphasis: { focus: 'series' }, cursor: 'pointer',
        })),
      }
    }
    case 'pie': {
      return {
        color: PALETTE,
        tooltip: tooltip(t, 'item'),
        legend: { ...legend(t, 'bottom'), bottom: 0, top: undefined },
        series: [{
          type: 'pie', radius: ['56%', '78%'], center: ['50%', '44%'], avoidLabelOverlap: true,
          itemStyle: { borderColor: dark ? '#0f1626' : '#fff', borderWidth: 3 },
          label: { show: false }, labelLine: { show: false }, cursor: 'pointer',
          emphasis: { scale: true, scaleSize: 6 },
          data: payload.data || [],
        }],
      }
    }
    case 'funnel': {
      return {
        color: PALETTE,
        tooltip: tooltip(t, 'item'),
        series: [{
          type: 'funnel', left: '8%', right: '8%', top: 16, bottom: 12, minSize: '24%', sort: 'descending', gap: 3,
          label: { color: '#fff', position: 'inside', formatter: '{b}: {c}', fontWeight: 600 },
          itemStyle: { borderWidth: 0 }, data: payload.data || [],
        }],
      }
    }
    case 'gauge': {
      const val = payload.value ?? 0
      const color = val >= 85 ? '#10b981' : val >= 65 ? '#f59e0b' : '#ef4444'
      return {
        series: [{
          type: 'gauge', startAngle: 210, endAngle: -30, min: 0, max: payload.max || 100, radius: '92%',
          progress: { show: true, width: 12, roundCap: true, itemStyle: { color } },
          axisLine: { lineStyle: { width: 12, color: [[1, t.split]] } },
          axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
          pointer: { show: false }, anchor: { show: false },
          title: { show: true, offsetCenter: [0, '40%'], color: t.text, fontSize: 12 },
          detail: {
            valueAnimation: true, offsetCenter: [0, '-2%'],
            formatter: (v) => `${Math.round(v)}${payload.unit || '%'}`,
            color: t.tooltipText, fontSize: 30, fontWeight: 800,
          },
          data: [{ value: val, name: payload.label || '' }],
        }],
      }
    }
    case 'heatmap': {
      const vals = (payload.data || []).map((d) => d[2])
      const max = payload.max || (vals.length ? Math.max(...vals) : 100)
      return {
        tooltip: { ...tooltip(t, 'item'), position: 'top' },
        grid: { left: 8, right: 16, top: 12, bottom: 56, containLabel: true },
        xAxis: { type: 'category', data: payload.x || [], ...axisLine(t, false), splitArea: { show: true } },
        yAxis: { type: 'category', data: payload.y || [], ...axisLine(t, false), splitArea: { show: true } },
        visualMap: {
          min: 0, max, calculable: true, orient: 'horizontal', left: 'center', bottom: 0,
          inRange: { color: ['#7f1d1d', '#b45309', '#15803d', '#10b981'] },
          textStyle: { color: t.text },
        },
        series: [{
          type: 'heatmap', data: payload.data || [],
          label: { show: true, color: '#fff', fontSize: 10, fontWeight: 600 },
          itemStyle: { borderColor: dark ? '#0f1626' : '#fff', borderWidth: 3, borderRadius: 6 },
          emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,.4)' } },
        }],
      }
    }
    default:
      return {}
  }
}
