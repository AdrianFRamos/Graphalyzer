import { computed, reactive, readonly } from 'vue'

import { api } from './api'

const STORAGE_KEY = 'graphalyzer:ultima-analise'

// A análise roda no backend local: sem ele não há como analisar nada novo.
// O que o PWA guarda é o último resultado, para consulta offline — que é o
// caso de uso real de uma ferramenta de documentação.
function persist(snapshot) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot))
  } catch {
    // cota estourada ou modo privativo: a sessão segue, só não sobrevive ao reload
  }
}

function restore() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
  } catch {
    return null
  }
}

const state = reactive({
  analysisId: null,
  project: null, // { project_name, project_path, file_count, ... }
  graph: { nodes: [], edges: [] },
  metrics: null,
  nodeDetails: null,
  nodeCache: {}, // detalhes já buscados, para funcionarem offline
  viewType: 'file',
  layout: 'cose',
  loading: null, // string com a mensagem, ou null
  error: null,
  offline: false,
  restoredFromCache: false,
})

const hasAnalysis = computed(() => state.project !== null)

const edgeCounts = computed(() => {
  const counts = {}
  for (const edge of state.graph.edges) {
    counts[edge.data.type] = (counts[edge.data.type] || 0) + 1
  }
  return counts
})

function snapshot() {
  return {
    analysisId: state.analysisId,
    project: state.project,
    graph: state.graph,
    metrics: state.metrics,
    nodeCache: state.nodeCache,
    viewType: state.viewType,
    savedAt: new Date().toISOString(),
  }
}

const actions = {
  /** Carrega o último resultado salvo neste dispositivo. */
  hydrate() {
    const saved = restore()
    if (!saved?.project) return false

    Object.assign(state, {
      analysisId: saved.analysisId,
      project: saved.project,
      graph: saved.graph || { nodes: [], edges: [] },
      metrics: saved.metrics,
      nodeCache: saved.nodeCache || {},
      viewType: saved.viewType || 'file',
      restoredFromCache: true,
    })
    return true
  },

  async analyze(projectPath, options = {}) {
    if (!projectPath?.trim()) {
      state.error = 'Informe o caminho do projeto.'
      return
    }

    state.loading = 'Analisando projeto...'
    state.error = null
    state.nodeDetails = null
    state.nodeCache = {}

    try {
      const result = await api.analyze(projectPath.trim(), options)
      state.analysisId = result.analysis_id
      state.project = result
      state.restoredFromCache = false
      state.offline = false

      await actions.loadGraph()
      await actions.loadMetrics()
      persist(snapshot())
    } catch (error) {
      state.error = error.message
      state.offline = error.status === 0
    } finally {
      state.loading = null
    }
  },

  async loadGraph() {
    if (!state.analysisId) return

    try {
      state.graph = await api.graph(state.analysisId, state.viewType)
      persist(snapshot())
    } catch (error) {
      state.error = error.message
      state.offline = error.status === 0
    }
  },

  async loadMetrics() {
    if (!state.analysisId) return

    try {
      state.metrics = await api.metrics(state.analysisId)
    } catch {
      // métricas são complementares: falha nelas não invalida o grafo
      state.metrics = null
    }
  },

  async setViewType(viewType) {
    state.viewType = viewType
    await actions.loadGraph()
  },

  setLayout(layout) {
    state.layout = layout
  },

  async selectNode(nodeId) {
    if (!nodeId) return

    if (state.nodeCache[nodeId]) {
      state.nodeDetails = state.nodeCache[nodeId]
      return
    }

    if (!state.analysisId) return

    try {
      const detail = await api.node(state.analysisId, nodeId)
      state.nodeCache[nodeId] = detail
      state.nodeDetails = detail
      persist(snapshot())
    } catch (error) {
      state.error = error.message
      state.offline = error.status === 0
    }
  },

  clearSelection() {
    state.nodeDetails = null
  },

  dismissError() {
    state.error = null
  },

  exportUrl(format) {
    return state.analysisId ? api.exportUrl(state.analysisId, format) : null
  },
}

export { actions, edgeCounts, hasAnalysis }
export const store = readonly(state)
export const mutableStore = state
