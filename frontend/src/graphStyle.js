// Estilo do grafo. Mesma linguagem visual do HTML exportado pelo backend:
// import cinza tracejado, chamada azul, fluxo de dados verde com a variável
// escrita em cima — é a aresta que dá sentido ao grafo.
export const cytoscapeStyle = [
  {
    selector: 'node',
    style: {
      content: 'data(label)',
      'text-valign': 'center',
      'text-halign': 'center',
      'background-color': 'data(color)',
      width: 60,
      height: 60,
      'font-size': 10,
      color: '#fff',
      'text-wrap': 'wrap',
      'text-max-width': 55,
      'border-width': 2,
      'border-color': '#fff',
    },
  },
  {
    selector: 'edge',
    style: {
      'target-arrow-shape': 'triangle',
      'line-color': '#ccc',
      'target-arrow-color': '#ccc',
      width: 2,
      'curve-style': 'bezier',
    },
  },
  {
    // Contenção (arquivo → função): estrutural, fica em segundo plano
    selector: 'edge[type = "uses"]',
    style: {
      'line-color': '#e2e8f0',
      'target-arrow-color': '#e2e8f0',
      width: 1,
    },
  },
  {
    selector: 'edge[type = "import"]',
    style: {
      'line-color': '#64748b',
      'target-arrow-color': '#64748b',
      'line-style': 'dashed',
    },
  },
  {
    selector: 'edge[type = "calls"]',
    style: {
      'line-color': '#3b82f6',
      'target-arrow-color': '#3b82f6',
    },
  },
  {
    selector: 'edge[type = "data_flow"]',
    style: {
      'line-color': '#22c55e',
      'target-arrow-color': '#22c55e',
      width: 3,
      label: 'data(label)',
      'font-size': 9,
      color: '#15803d',
      'text-background-color': '#fff',
      'text-background-opacity': 0.85,
      'text-background-padding': 2,
    },
  },
  {
    selector: 'node:selected',
    style: {
      'background-color': '#ef4444',
      width: 80,
      height: 80,
      'border-width': 3,
      'border-color': '#b91c1c',
    },
  },
  {
    selector: 'edge:selected',
    style: {
      'line-color': '#ef4444',
      'target-arrow-color': '#ef4444',
      width: 3,
    },
  },
]

export const EDGE_LEGEND = [
  { type: 'data_flow', color: '#22c55e', label: 'Fluxo de dados' },
  { type: 'calls', color: '#3b82f6', label: 'Chamada' },
  { type: 'import', color: '#64748b', label: 'Import' },
  { type: 'uses', color: '#cbd5e1', label: 'Contém' },
]

export function layoutOptions(name) {
  return {
    name,
    directed: true,
    animate: true,
    animationDuration: 400,
    fit: true,
    padding: 30,
  }
}
