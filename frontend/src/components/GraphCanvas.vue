<script setup>
import cola from 'cytoscape-cola'
import coseBilkent from 'cytoscape-cose-bilkent'
import fcose from 'cytoscape-fcose'
import cytoscape from 'cytoscape'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import {
  CORES,
  EDGE_LEGEND,
  LIMITE_FISICA_VIVA,
  coresPorPasta,
  grupoDaPasta,
  cytoscapeStyle,
  layoutOptions,
} from '@/graphStyle'
import { actions, store } from '@/store'

cytoscape.use(coseBilkent)
cytoscape.use(cola)
cytoscape.use(fcose)

const container = ref(null)
const legendaAberta = ref(true)
const pastas = ref([]) // [{ pasta, cor, total }] para a legenda
const pastaEmFoco = ref(null)
let cy = null
let simulacao = null

// Abaixo deste zoom o grafo vira só pontos, como no Obsidian
const ZOOM_DOS_ROTULOS = 1.4

const copiar = (v) => JSON.parse(JSON.stringify(v))

function aplicarDadosVisuais() {
  // Tamanho vem do número de conexões; cor, da pasta. Sem isso todos os nós
  // ficam iguais e o grafo perde a leitura de "o que é central" e "de onde vem".
  const cores = coresPorPasta(store.graph.nodes)
  const profundidade = cores.profundidade

  // Legenda ordenada por quantidade: os grupos que dominam o grafo primeiro
  const contagem = new Map()
  for (const n of store.graph.nodes) {
    const grupo = grupoDaPasta(n.data.folder || '', profundidade)
    contagem.set(grupo, (contagem.get(grupo) || 0) + 1)
  }
  pastas.value = [...contagem.entries()]
    .map(([pasta, total]) => ({ pasta, total, cor: cores.get(pasta) }))
    .sort((a, b) => b.total - a.total)

  cy.batch(() => {
    cy.nodes().forEach((n) => {
      n.data('grau', n.degree(false))
      const grupo = grupoDaPasta(n.data('folder') || '', profundidade)
      n.data('grupoDaPasta', grupo)
      n.data('corDaPasta', cores.get(grupo) || CORES.no)
    })
  })
}

/** Órfãos vão para um anel externo, em vez de vagarem pelo centro.
 *
 * Ficam travados depois de posicionados: o layout de força continua rodando e,
 * sem a trava, empurraria todos de volta para uma fileira.
 */
function anelDeOrfaos(orfaos, conectados) {
  if (!orfaos.length) return

  const caixa = conectados.length
    ? conectados.boundingBox()
    : { x1: 0, y1: 0, w: 0, h: 0 }

  const cx = caixa.x1 + caixa.w / 2
  const cy0 = caixa.y1 + caixa.h / 2

  // O raio acompanha a quantidade: com 119 órfãos num anel pequeno eles se
  // sobrepõem. ~14px de arco por nó mantém o espaçamento legível.
  const raioMinimo = (orfaos.length * 14) / (2 * Math.PI)
  const raio = Math.max(Math.max(caixa.w, caixa.h) / 2 + 80, raioMinimo)

  orfaos.forEach((n, i) => {
    const angulo = (2 * Math.PI * i) / orfaos.length - Math.PI / 2
    n.unlock()
    n.position({ x: cx + raio * Math.cos(angulo), y: cy0 + raio * Math.sin(angulo) })
    n.lock()
  })
}

/** Enquadra o miolo conectado, não o anel de órfãos.
 *
 * Enquadrar tudo faz o anel externo dominar a tela e o grafo de verdade fica
 * minúsculo no centro — era o motivo do zoom parecer distante demais.
 */
function enquadrar(conectados) {
  const alvo = conectados && conectados.length ? conectados : cy.nodes()
  cy.fit(alvo, 40)

  // Enquadrar um grafo denso ainda pode deixar tudo pequeno demais para clicar
  if (cy.zoom() < 0.55) cy.zoom({ level: 0.55, position: alvo.boundingBox() && cy.pan() })
  atualizarRotulos()
}

function pararSimulacao() {
  if (simulacao) {
    simulacao.stop()
    simulacao = null
  }
}

function rodarLayout() {
  if (!cy || !cy.nodes().length) return

  pararSimulacao()
  aplicarDadosVisuais()
  cy.nodes().unlock()

  const orfaos = cy.nodes().filter((n) => n.degree(false) === 0)
  const conectados = cy.nodes().difference(orfaos)

  // Sem nenhuma conexão não há o que simular: só o anel, e pronto.
  if (!conectados.length) {
    anelDeOrfaos(orfaos, conectados)
    cy.fit(undefined, 60)
    return
  }


  // Física viva só cabe em grafo pequeno; acima disso o navegador não aguenta
  const escolhido =
    store.layout === 'cola' && cy.nodes().length > LIMITE_FISICA_VIVA
      ? 'fcose'
      : store.layout

  const alvo = conectados.union(conectados.connectedEdges())
  simulacao = alvo.layout(layoutOptions(escolhido, cy.nodes().length))

  const finalizar = () => {
    anelDeOrfaos(orfaos, conectados)
    enquadrar(conectados)
  }

  simulacao.on('layoutstop', finalizar)
  simulacao.run()

  // O layout contínuo nunca emite `layoutstop`
  if (escolhido === 'cola') setTimeout(finalizar, 1200)
}

function render() {
  if (!cy) return

  pararSimulacao()
  cy.elements().remove()

  // Cópia profunda antes de entregar ao Cytoscape: o store é `readonly`, e o
  // proxy do Vue bloqueia silenciosamente qualquer escrita. Passando a
  // referência direta, `node.data('grau', ...)` não gravava nada e todos os
  // nós saíam com o tamanho padrão — o dimensionamento por conexões sumia.
  //
  // Round-trip de JSON, não `structuredClone`: este último não sabe clonar o
  // Proxy do Vue e estoura DataCloneError. Os dados vêm da API como JSON puro,
  // então a serialização é fiel.
  cy.add(copiar(store.graph.nodes))
  cy.add(copiar(store.graph.edges))

  rodarLayout()
}

function atualizarRotulos() {
  if (!cy) return
  const mostrar = cy.zoom() >= ZOOM_DOS_ROTULOS
  cy.batch(() => {
    cy.nodes().toggleClass('com-rotulo', mostrar)
  })
}

function focar(no) {
  if (pastaEmFoco.value !== null) return
  const vizinhanca = no.closedNeighborhood()
  cy.batch(() => {
    cy.elements().addClass('apagado')
    vizinhanca.removeClass('apagado').addClass('vizinho')
    no.removeClass('vizinho').addClass('foco')
  })
}

/** Clicar numa pasta da legenda isola os nós dela. */
function alternarPasta(pasta) {
  pastaEmFoco.value = pastaEmFoco.value === pasta ? null : pasta

  cy.batch(() => {
    cy.elements().removeClass('apagado vizinho foco')

    if (pastaEmFoco.value === null) return

    const daPasta = cy.nodes().filter((n) => n.data('grupoDaPasta') === pastaEmFoco.value)
    cy.elements().addClass('apagado')
    daPasta.union(daPasta.connectedEdges()).removeClass('apagado')
  })
}

function limparFoco() {
  // Um foco por pasta é deliberado: não pode ser desfeito ao tirar o mouse
  if (pastaEmFoco.value !== null) return

  cy.batch(() => {
    cy.elements().removeClass('apagado vizinho foco')
  })
}

onMounted(() => {
  cy = cytoscape({
    container: container.value,
    elements: [],
    style: cytoscapeStyle(),
    wheelSensitivity: 0.2,
    minZoom: 0.08,
    maxZoom: 6,
  })

  cy.on('mouseover', 'node', (e) => focar(e.target))
  cy.on('mouseout', 'node', limparFoco)

  cy.on('tap', 'node', (e) => actions.selectNode(e.target.id()))
  cy.on('tap', (e) => {
    if (e.target === cy) {
      limparFoco()
      actions.clearSelection()
    }
  })

  cy.on('zoom', atualizarRotulos)

  // Grafo acessível pelo console: dá para inspecionar posições, medir o layout
  // e automatizar sem precisar de gancho de depuração espalhado pelo código.
  window.cy = cy

  render()
})

onBeforeUnmount(() => {
  pararSimulacao()
  cy?.destroy()
})

watch(() => store.graph, render, { deep: true })
watch(() => store.layout, rodarLayout)

// Selecionar na lista lateral destaca o nó no grafo
watch(
  () => store.nodeDetails?.id,
  (nodeId) => {
    if (!cy) return
    cy.elements().unselect()
    if (!nodeId) return

    const no = cy.getElementById(nodeId)
    if (no.nonempty()) {
      no.select()
      cy.animate({ center: { eles: no }, duration: 300 })
    }
  },
)
</script>

<template>
  <div class="canvas-wrap">
    <div ref="container" class="canvas" />

    <button
      class="legenda-toggle"
      :aria-expanded="legendaAberta"
      @click="legendaAberta = !legendaAberta"
    >
      {{ legendaAberta ? '⌄' : '⌃' }} Legenda
    </button>

    <ul v-if="legendaAberta" class="legend">
      <li v-for="item in EDGE_LEGEND" :key="item.type">
        <span class="swatch" :style="{ background: item.color }" />
        {{ item.label }}
      </li>
      <li class="dica">Tamanho do nó = nº de conexões · zoom mostra os nomes</li>
    </ul>

    <div v-if="legendaAberta && pastas.length" class="legend pastas">
      <strong>Pastas</strong>
      <ul>
        <li
          v-for="p in pastas"
          :key="p.pasta"
          :class="{ ativa: pastaEmFoco === p.pasta }"
          @click="alternarPasta(p.pasta)"
        >
          <span class="bola" :style="{ background: p.cor }" />
          <span class="nome" :title="p.pasta || '(raiz)'">{{ p.pasta || '(raiz)' }}</span>
          <span class="total">{{ p.total }}</span>
        </li>
      </ul>
    </div>

    <p v-if="!store.graph.nodes.length" class="empty">
      Nenhum grafo carregado. Informe o caminho de um projeto acima — Python,
      Dart, TypeScript, Go, Java e mais.
    </p>
  </div>
</template>

<style scoped>
.canvas-wrap {
  position: relative;
  flex: 1;
  min-height: 0;
  /* O fundo escuro é parte da leitura do grafo: pontos claros sobre escuro */
  background: v-bind('CORES.fundo');
}

.canvas {
  width: 100%;
  height: 100%;
}

.legenda-toggle {
  position: absolute;
  bottom: 0.75rem;
  left: 0.75rem;
  z-index: 2;
  padding: 0.25rem 0.5rem;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: rgba(26, 27, 38, 0.85);
  color: #8b93a7;
  font-size: 0.7rem;
  cursor: pointer;
}

.legend {
  position: absolute;
  bottom: 2.6rem;
  left: 0.75rem;
  z-index: 2;
  margin: 0;
  padding: 0.6rem 0.75rem;
  list-style: none;
  display: grid;
  gap: 0.35rem;
  background: rgba(26, 27, 38, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  font-size: 0.72rem;
  color: #a9b1d6;
}

.legend li {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.swatch {
  width: 16px;
  height: 3px;
  border-radius: 2px;
}

.legend.pastas {
  bottom: auto;
  top: 0.75rem;
  left: auto;
  right: 0.75rem;
  display: block;
  max-height: 45vh;
  overflow-y: auto;
  padding: 0.6rem 0.7rem;
}

.legend.pastas strong {
  display: block;
  margin-bottom: 0.4rem;
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #7d86a4;
}

.legend.pastas ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.15rem;
}

.legend.pastas li {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 0.45rem;
  padding: 0.15rem 0.3rem;
  border-radius: 4px;
  cursor: pointer;
}

.legend.pastas li:hover {
  background: rgba(255, 255, 255, 0.06);
}

.legend.pastas li.ativa {
  background: rgba(255, 255, 255, 0.12);
}

.bola {
  width: 9px;
  height: 9px;
  border-radius: 50%;
}

.nome {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 190px;
}

.total {
  color: #6b7394;
  font-variant-numeric: tabular-nums;
  font-size: 0.66rem;
}

.dica {
  margin-top: 0.2rem;
  padding-top: 0.4rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  color: #6b7394;
  font-size: 0.67rem;
}

.empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  margin: 0;
  padding: 2rem;
  text-align: center;
  color: #6b7394;
  pointer-events: none;
}
</style>
