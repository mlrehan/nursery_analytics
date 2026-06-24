// Builds Apache ECharts option objects from the backend payload contract.
// Every chart in the app is rendered by ECharts (mandatory).

const PALETTE = ['#3366ff', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#14b8a6']

function theme(dark) {
  return {
    text: dark ? '#cbd5e1' : '#334155',
    axis: dark ? '#1e293b' : '#e2e8f0',
    split: dark ? '#1e293b' : '#eef2f7',
    tooltipBg: dark ? '#0f172a' : '#ffffff',
    tooltipBorder: dark ? '#1e293b' : '#e2e8f0',
  }
}

const baseGrid = { left: 48, right: 20, top: 36, bottom: 36, containLabel: true }

function tooltip(t, trigger = 'axis') {
  return {
    trigger,
    backgroundColor: t.tooltipBg,
    borderColor: t.tooltipBorder,
    textStyle: { color: t.text, fontSize: 12 },
  }
}

function legend(t, top = 'top') {
  return { top, textStyle: { color: t.text }, icon: 'roundRect', itemWidth: 10, itemHeight: 10 }
}

function axisLine(t) {
  return {
    axisLine: { lineStyle: { color: t.axis } },
    axisLabel: { color: t.text, fontSize: 11 },
    splitLine: { lineStyle: { color: t.split } },
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
        xAxis: { type: 'category', boundaryGap: false, data: payload.x || [], ...axisLine(t) },
        yAxis: { type: 'value', ...axisLine(t) },
        series: (payload.series || []).map((s, i) => ({
          name: s.name, type: 'line', smooth: true, showSymbol: false,
          data: s.data, connectNulls: false,
          areaStyle: i === 0 ? { opacity: 0.1 } : undefined,
          lineStyle: i === 1 ? { width: 2, type: 'dashed' } : { width: 2.5 },
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
        xAxis: { type: 'category', data: payload.categories || [], ...axisLine(t) },
        yAxis: { type: 'value', ...axisLine(t) },
        series: (payload.series || []).map((s) => ({
          name: s.name, type: 'bar', data: s.data,
          stack: stacked ? 'total' : undefined,
          barMaxWidth: 38, itemStyle: { borderRadius: stacked ? 0 : [4, 4, 0, 0] },
        })),
      }
    }
    case 'pie': {
      return {
        color: PALETTE,
        tooltip: tooltip(t, 'item'),
        legend: { ...legend(t, 'bottom'), bottom: 0 },
        series: [{
          type: 'pie', radius: ['52%', '74%'], center: ['50%', '46%'], avoidLabelOverlap: true,
          itemStyle: { borderColor: dark ? '#0f172a' : '#fff', borderWidth: 2 },
          label: { show: false }, labelLine: { show: false },
          data: payload.data || [],
        }],
      }
    }
    case 'funnel': {
      return {
        color: PALETTE,
        tooltip: tooltip(t, 'item'),
        legend: legend(t),
        series: [{
          type: 'funnel', left: '10%', right: '10%', top: 40, bottom: 10,
          minSize: '20%', sort: 'descending', gap: 2,
          label: { color: t.text, position: 'inside', formatter: '{b}: {c}' },
          data: payload.data || [],
        }],
      }
    }
    case 'gauge': {
      const val = payload.value ?? 0
      const color = val >= 85 ? '#22c55e' : val >= 65 ? '#f59e0b' : '#ef4444'
      return {
        series: [{
          type: 'gauge', startAngle: 210, endAngle: -30, min: 0, max: payload.max || 100,
          progress: { show: true, width: 14, itemStyle: { color } },
          axisLine: { lineStyle: { width: 14, color: [[1, t.split]] } },
          axisTick: { show: false }, splitLine: { show: false },
          axisLabel: { show: false }, pointer: { show: false },
          anchor: { show: false },
          title: { show: true, offsetCenter: [0, '36%'], color: t.text, fontSize: 12 },
          detail: {
            valueAnimation: true, offsetCenter: [0, '-4%'],
            formatter: (v) => `${Math.round(v)}${payload.unit || '%'}`,
            color: t.text, fontSize: 26, fontWeight: 700,
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
        grid: { left: 60, right: 20, top: 20, bottom: 50, containLabel: true },
        xAxis: { type: 'category', data: payload.x || [], ...axisLine(t), splitArea: { show: true } },
        yAxis: { type: 'category', data: payload.y || [], ...axisLine(t), splitArea: { show: true } },
        visualMap: {
          min: 0, max, calculable: true, orient: 'horizontal', left: 'center', bottom: 0,
          inRange: { color: ['#fee2e2', '#fde68a', '#86efac', '#22c55e'] },
          textStyle: { color: t.text },
        },
        series: [{
          type: 'heatmap', data: payload.data || [],
          label: { show: true, color: '#0f172a', fontSize: 10 },
          itemStyle: { borderColor: dark ? '#0f172a' : '#fff', borderWidth: 2 },
        }],
      }
    }
    default:
      return {}
  }
}
