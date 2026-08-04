// Cliente da API. Caminho relativo: o dashboard é servido pela própria API,
// então funciona em qualquer porta e dispensa CORS.
const API_BASE = '/api'

class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, options)
  } catch (cause) {
    // fetch só rejeita por falha de rede — a API local está fora do ar
    throw new ApiError('Não foi possível falar com a API local.', 0)
  }

  if (!response.ok) {
    // O FastAPI devolve o motivo em `detail`; sem ele, sobra o status
    const detail = await response
      .json()
      .then((body) => body.detail)
      .catch(() => null)
    throw new ApiError(detail || `Erro ${response.status}`, response.status)
  }

  return response.json()
}

export const api = {
  analyze(projectPath, { useAi = false } = {}) {
    return request('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_path: projectPath, use_ai: useAi }),
    })
  },

  graph(analysisId, viewType) {
    return request(`/analysis/${analysisId}/graph?view_type=${viewType}`)
  },

  // IDs de nó contêm "::" e separadores de caminho — precisam ser escapados
  node(analysisId, nodeId) {
    return request(`/analysis/${analysisId}/node/${encodeURIComponent(nodeId)}`)
  },

  metrics(analysisId) {
    return request(`/analysis/${analysisId}/metrics`)
  },

  exportUrl(analysisId, format) {
    return `${API_BASE}/analysis/${analysisId}/export/${format}`
  },

  statusDaIA() {
    return request('/ai/status')
  },

  // A chave sobe uma vez e fica na memória do servidor; nunca volta.
  definirChave(chave, provedor = 'claude') {
    return request('/ai/key', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provedor, chave }),
    })
  },

  esquecerChave(provedor = 'claude') {
    return request(`/ai/key?provedor=${provedor}`, { method: 'DELETE' })
  },

  async online() {
    try {
      const response = await fetch('/health')
      return response.ok
    } catch {
      return false
    }
  },
}

export { ApiError }
