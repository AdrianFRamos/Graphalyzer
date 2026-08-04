import { computed, reactive, readonly } from 'vue'

import { api } from './api'

const STORAGE_KEY = 'graphalyzer:ultima-analise'

// Subir este número descarta snapshots gravados por versões antigas. Sem isso,
// um campo novo (como a pasta do nó) fica faltando no que veio do disco e a
// tela mostra dados incompletos sem nenhum sinal de erro.
const VERSAO_DO_SNAPSHOT = 2

// Preferência de tema fica fora do snapshot da análise: sobrevive à troca de
// projeto e a qualquer mudança de formato dos dados.
const CHAVE_DO_TEMA = 'graphalyzer:tema'

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
    const dados = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    if (dados?.versao !== VERSAO_DO_SNAPSHOT) return null
    return dados
  } catch {
    return null
  }
}

const state = reactive({
  analysisId: null,
  project: null, // { project_name, project_path, file_count, ... }
  projectPath: '', // caminho submetido, para reanalisar sem depender da resposta
  graph: { nodes: [], edges: [] },
  metrics: null,
  nodeDetails: null,
  nodeCache: {}, // detalhes já buscados, para funcionarem offline
  viewType: 'file',
  layout: 'fcose', // rápido e estável mesmo com milhares de nós
  loading: null, // string com a mensagem, ou null
  error: null,
  offline: false,
  restoredFromCache: false,
  _revalidando: false,
  tema: localStorage.getItem(CHAVE_DO_TEMA) || 'auto', // auto | claro | escuro
  ia: null, // { configurada, origem, sdk_disponivel, modelo }
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
    projectPath: state.projectPath,
    graph: state.graph,
    metrics: state.metrics,
    nodeCache: state.nodeCache,
    viewType: state.viewType,
    versao: VERSAO_DO_SNAPSHOT,
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
      projectPath: saved.projectPath || saved.project?.project_path || '',
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
      state.projectPath = result.project_path || projectPath.trim()
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

  /** Refaz a análise quando o servidor não conhece mais o id guardado.
   *
   * A store de análises do servidor é em memória e morre a cada reinício,
   * enquanto o navegador guarda o id em localStorage. Sem isto o usuário
   * ficaria olhando um grafo velho e recebendo 404 em silêncio. A reanálise é
   * barata porque o cache em disco do servidor sobrevive ao reinício.
   */
  async _revalidar() {
    const caminho = state.projectPath || state.project?.project_path
    if (!caminho || state._revalidando) return false

    state._revalidando = true
    try {
      const result = await api.analyze(caminho)
      state.analysisId = result.analysis_id
      state.project = result
      state.projectPath = result.project_path || caminho
      return true
    } catch {
      return false
    } finally {
      state._revalidando = false
    }
  },

  async loadGraph() {
    if (!state.analysisId) return

    try {
      state.graph = await api.graph(state.analysisId, state.viewType)
      persist(snapshot())
    } catch (error) {
      if (error.status === 404 && (await actions._revalidar())) {
        return actions.loadGraph()
      }
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

  async carregarStatusDaIA() {
    try {
      state.ia = await api.statusDaIA()
    } catch {
      state.ia = null
    }
  },

  /** Envia a chave ao servidor local. Nunca é guardada no navegador:
   *  localStorage é legível por qualquer script da página. */
  async salvarChaveDaIA(chave) {
    state.ia = await api.definirChave(chave)
  },

  async esquecerChaveDaIA() {
    state.ia = await api.esquecerChave()
  },

  /** Aplica o tema no <html>; "auto" remove o atributo e devolve ao sistema. */
  setTema(tema) {
    state.tema = tema
    try {
      localStorage.setItem(CHAVE_DO_TEMA, tema)
    } catch {
      // modo privativo: vale só para esta sessão
    }
    aplicarTema(tema)
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
      if (error.status === 404 && (await actions._revalidar())) {
        return actions.selectNode(nodeId)
      }
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

function aplicarTema(tema) {
  const raiz = document.documentElement
  if (tema === 'auto') raiz.removeAttribute('data-theme')
  else raiz.dataset.theme = tema
}

// Aplica antes do primeiro render, senão a tela pisca no tema errado
aplicarTema(state.tema)

export { actions, edgeCounts, hasAnalysis }
export const store = readonly(state)
export const mutableStore = state
