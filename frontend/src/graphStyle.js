// Estilo do grafo, no espírito do "graph view" do Obsidian: pontos pequenos
// dimensionados pelo número de conexões, links finos sem seta, rótulo só
// quando há zoom, e o resto apagado quando algo está em foco.

// O Cytoscape desenha em canvas e não enxerga variável CSS: os valores
// precisam ser lidos do documento e repassados como cor literal.
function lerVariavel(nome, alternativa) {
  if (typeof document === 'undefined') return alternativa
  const valor = getComputedStyle(document.documentElement)
    .getPropertyValue(nome)
    .trim()
  return valor || alternativa
}

// No Obsidian a maioria dos nós é neutra e a cor é exceção. Tingir tudo por
// tipo deixa o grafo com cara de diagrama, não de constelação.
export function cores() {
  return {
    fundo: lerVariavel('--grafo-fundo', '#191a23'),
    no: lerVariavel('--grafo-no', '#c3c9dd'),
    link: lerVariavel('--grafo-link', '#454b66'),
    texto: lerVariavel('--grafo-texto', '#d5dbf0'),
    contorno: lerVariavel('--grafo-contorno', '#e8ecfb'),
    // Estes não mudam com o tema: são matizes médios, legíveis nos dois
    data_flow: '#4c7a63',
    calls: '#42597f',
    import: '#5b5478',
    destaque: '#f7768e',
  }
}

// Grau -> diâmetro. É a marca visual do Obsidian: o que é muito referenciado
// aparece grande sem precisar de rótulo.
const TAMANHO_MIN = 7
const TAMANHO_MAX = 38

// Paleta para colorir por pasta. Matizes bem separados e saturação parecida,
// para nenhuma pasta parecer mais importante que outra.
export const PALETA_PASTAS = [
  '#7aa2f7',
  '#9ece6a',
  '#e0af68',
  '#bb9af7',
  '#7dcfff',
  '#f7768e',
  '#73daca',
  '#ff9e64',
  '#c0caf5',
  '#b4f9f8',
  '#d19a66',
  '#a6e3a1',
  '#f5c2e7',
  '#89dceb',
  '#eba0ac',
  '#94e2d5',
]

/** Agrupa a pasta até a profundidade pedida: `a/b/c/d` com 2 vira `a/b`. */
export function grupoDaPasta(pasta, profundidade) {
  return (pasta || '').split('/').slice(0, profundidade).join('/')
}

/** Profundidade que melhor separa as pastas sem esgotar a paleta.
 *
 * Colorir pela pasta completa parece o certo, mas um projeto real tem dezenas
 * de subpastas: as cores passam a se repetir e deixam de significar algo.
 * Pega-se a maior profundidade cujos grupos ainda cabem na paleta.
 */
export function profundidadeIdeal(nodes) {
  const pastas = nodes.map((n) => n.data.folder || '')
  let escolhida = 1

  for (let d = 1; d <= 6; d++) {
    const grupos = new Set(pastas.map((p) => grupoDaPasta(p, d)))
    if (grupos.size > PALETA_PASTAS.length) break
    escolhida = d
    // Já separou tudo o que havia para separar
    if (grupos.size === new Set(pastas).size) break
  }

  return escolhida
}

/** Mapa grupo-de-pasta -> cor, estável: o mesmo grupo recebe sempre a mesma cor. */
export function coresPorPasta(nodes, profundidade = null) {
  const d = profundidade ?? profundidadeIdeal(nodes)
  const grupos = [
    ...new Set(nodes.map((n) => grupoDaPasta(n.data.folder || '', d))),
  ].sort()

  const mapa = new Map()
  grupos.forEach((grupo, i) => {
    mapa.set(grupo, PALETA_PASTAS[i % PALETA_PASTAS.length])
  })
  mapa.profundidade = d

  return mapa
}

export function cytoscapeStyle() {
  const CORES = cores()

  return [
    {
      selector: 'node',
      style: {
        // A cor vem da pasta (atribuída no canvas); o tipo deixa de pintar
        'background-color': 'data(corDaPasta)',
        width: `mapData(grau, 0, 20, ${TAMANHO_MIN}, ${TAMANHO_MAX})`,
        height: `mapData(grau, 0, 20, ${TAMANHO_MIN}, ${TAMANHO_MAX})`,
        'border-width': 0,
        label: 'data(label)',
        'font-size': 7,
        'text-valign': 'bottom',
        'text-margin-y': 4,
        color: CORES.texto,
        'text-opacity': 0, // só aparece com zoom ou foco
        'text-outline-width': 2,
        'text-outline-color': CORES.fundo,
        'min-zoomed-font-size': 6,
        'transition-property': 'opacity, background-color',
        'transition-duration': '120ms',
      },
    },
    // Arquivo ganha contorno para se distinguir de função/classe sem mudar
    // a cor, que agora significa pasta
    {
      selector: 'node[type = "file"]',
      style: { 'border-width': 2, 'border-color': CORES.contorno, 'border-opacity': 0.55 },
    },
    {
      selector: 'edge',
      style: {
        width: 0.6,
        'line-color': CORES.link,
        'curve-style': 'straight',
        'target-arrow-shape': 'none', // Obsidian não desenha setas
        opacity: 0.55,
        'transition-property': 'opacity, line-color',
        'transition-duration': '120ms',
      },
    },
    // O tipo da aresta continua legível, mas discreto: o fluxo de dados é o
    // que dá sentido ao grafo e não pode sumir no visual novo.
    {
      selector: 'edge[type = "data_flow"]',
      style: { 'line-color': CORES.data_flow, width: 0.9 },
    },
    { selector: 'edge[type = "calls"]', style: { 'line-color': CORES.calls } },
    {
      selector: 'edge[type = "import"]',
      style: { 'line-color': CORES.import, 'line-style': 'dashed' },
    },

    // Rótulos ligados por zoom
    { selector: 'node.com-rotulo', style: { 'text-opacity': 0.9 } },

    // Foco: o alvo e a vizinhança acesos, o resto apagado
    { selector: '.apagado', style: { opacity: 0.08, 'text-opacity': 0 } },
    {
      selector: 'node.vizinho',
      style: { 'text-opacity': 0.95, 'z-index': 10 },
    },
    {
      selector: 'node.foco',
      style: {
        'background-color': CORES.destaque,
        'text-opacity': 1,
        'border-width': 2,
        'border-color': CORES.destaque,
        'border-opacity': 0.35,
        'z-index': 20,
      },
    },
    {
      selector: 'edge.vizinho',
      style: { opacity: 1, width: 1.4, 'line-color': CORES.destaque },
    },
    {
      selector: 'node:selected',
      style: {
        'background-color': CORES.destaque,
        'text-opacity': 1,
        'z-index': 20,
      },
    },
  ]
}

export function edgeLegend() {
  const c = cores()
  return [
    { type: 'data_flow', color: c.data_flow, label: 'Fluxo de dados' },
    { type: 'calls', color: c.calls, label: 'Chamada' },
    { type: 'import', color: c.import, label: 'Import' },
    { type: 'uses', color: c.link, label: 'Contém' },
  ]
}

// Acima deste tamanho, simulação contínua trava o navegador — um projeto real
// chega fácil a 4 mil nós.
export const LIMITE_FISICA_VIVA = 700

export function layoutOptions(nome, quantidadeDeNos = 0) {
  // `handleDisconnected` fica desligado em todos: os órfãos são posicionados
  // à parte, num anel. Ligado, o cola alinha os desconectados numa fileira —
  // era isso que transformava o grafo numa linha de pontos.
  if (nome === 'cola') {
    return {
      name: 'cola',
      animate: true,
      infinite: true, // a simulação não termina: arrastar reorganiza os vizinhos
      fit: false,
      nodeSpacing: 8,
      edgeLength: 70,
      randomize: true,
      handleDisconnected: false,
      convergenceThreshold: 0.01,
    }
  }

  if (nome === 'fcose') {
    return {
      name: 'fcose',
      quality: quantidadeDeNos > 2000 ? 'draft' : 'default',
      animate: false, // animar milhares de nós custa mais que o layout
      randomize: true,
      fit: true,
      padding: 60,
      nodeRepulsion: 6000,
      idealEdgeLength: 60,
      edgeElasticity: 0.35,
      gravity: 0.3,
      numIter: quantidadeDeNos > 2000 ? 1200 : 2500,
    }
  }

  if (nome === 'cose-bilkent') {
    return {
      name: 'cose-bilkent',
      animate: 'end',
      animationDuration: 500,
      randomize: true,
      nodeRepulsion: 6000,
      idealEdgeLength: 60,
      fit: true,
      padding: 50,
    }
  }

  return { name: nome, animate: true, animationDuration: 400, fit: true, padding: 50 }
}
