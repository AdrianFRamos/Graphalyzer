<script setup>
import coseBilkent from 'cytoscape-cose-bilkent'
import cytoscape from 'cytoscape'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { EDGE_LEGEND, cytoscapeStyle, layoutOptions } from '@/graphStyle'
import { actions, store } from '@/store'

cytoscape.use(coseBilkent)

const container = ref(null)
let cy = null

function render() {
  if (!cy) return

  cy.elements().remove()
  cy.add(store.graph.nodes)
  cy.add(store.graph.edges)
  cy.layout(layoutOptions(store.layout)).run()
}

onMounted(() => {
  cy = cytoscape({
    container: container.value,
    elements: [],
    style: cytoscapeStyle,
    // `wheelSensitivity` baixo evita que um scroll de trackpad jogue o zoom
    // para o extremo
    wheelSensitivity: 0.2,
  })

  cy.on('tap', 'node', (event) => actions.selectNode(event.target.id()))
  cy.on('tap', (event) => {
    if (event.target === cy) actions.clearSelection()
  })

  render()
})

onBeforeUnmount(() => cy?.destroy())

watch(() => store.graph, render, { deep: true })
watch(
  () => store.layout,
  (layout) => cy?.layout(layoutOptions(layout)).run(),
)

// Selecionar na lista lateral deve destacar o nó no grafo
watch(
  () => store.nodeDetails?.id,
  (nodeId) => {
    if (!cy) return
    cy.elements().unselect()
    if (nodeId) cy.getElementById(nodeId).select()
  },
)

defineExpose({ fit: () => cy?.fit(undefined, 30) })
</script>

<template>
  <div class="canvas-wrap">
    <div ref="container" class="canvas" />

    <ul class="legend">
      <li v-for="item in EDGE_LEGEND" :key="item.type">
        <span class="swatch" :style="{ background: item.color }" />
        {{ item.label }}
      </li>
    </ul>

    <p v-if="!store.graph.nodes.length" class="empty">
      Nenhum grafo carregado. Informe o caminho de um projeto acima — Python, Dart, TypeScript, Go, Java e mais.
    </p>
  </div>
</template>

<style scoped>
.canvas-wrap {
  position: relative;
  flex: 1;
  min-height: 0;
}

.canvas {
  width: 100%;
  height: 100%;
  background: var(--surface);
}

.legend {
  position: absolute;
  bottom: 1rem;
  left: 1rem;
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin: 0;
  padding: 0.5rem 0.75rem;
  list-style: none;
  background: color-mix(in srgb, var(--surface) 90%, transparent);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.legend li {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.swatch {
  width: 14px;
  height: 3px;
  border-radius: 2px;
}

.empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  margin: 0;
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
  pointer-events: none;
}
</style>
