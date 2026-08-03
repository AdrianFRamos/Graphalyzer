<script setup>
import { computed, ref } from 'vue'

import { actions, edgeCounts, store } from '@/store'

const filtro = ref('')

const EDGE_LABELS = {
  data_flow: 'Fluxo de dados',
  calls: 'Chamadas',
  import: 'Imports',
  uses: 'Contenção',
}

const nosFiltrados = computed(() => {
  const termo = filtro.value.trim().toLowerCase()
  const nodes = store.graph.nodes
  if (!termo) return nodes
  return nodes.filter((n) => n.data.label.toLowerCase().includes(termo))
})

const metricas = computed(() => {
  if (!store.metrics) return []
  const { architecture, quality } = store.metrics
  const pct = (v) => `${(v * 100).toFixed(1)}%`
  return [
    ['Complexidade média', architecture.cyclomatic_complexity.toFixed(2)],
    ['Acoplamento', pct(architecture.coupling)],
    ['Coesão', pct(architecture.cohesion)],
    ['Documentação', pct(quality.documentation_coverage)],
    ['Type hints', pct(quality.type_hints_coverage)],
  ]
})

const estatisticas = computed(() => {
  const p = store.project
  if (!p) return []
  return [
    ['Arquivos', p.file_count],
    ['Funções', p.function_count],
    ['Classes', p.class_count],
    ['Arestas', p.edge_count],
  ]
})

const EXPORTS = [
  ['json', '📥 JSON'],
  ['md', '📝 Markdown'],
  ['html', '🌐 HTML'],
  ['csv', '📊 CSV'],
]
</script>

<template>
  <aside class="panel">
    <h1 class="logo">📊 Graphalyzer</h1>

    <section v-if="store.project" class="project">
      <h2>{{ store.project.project_name }}</h2>
      <p class="path">{{ store.project.project_path }}</p>

      <ul class="stats">
        <li v-for="[label, value] in estatisticas" :key="label">
          <strong>{{ value }}</strong>
          <span>{{ label }}</span>
        </li>
      </ul>

      <ul v-if="Object.keys(edgeCounts).length" class="edge-counts">
        <li v-for="(count, type) in edgeCounts" :key="type">
          <span>{{ EDGE_LABELS[type] || type }}</span>
          <strong>{{ count }}</strong>
        </li>
      </ul>
    </section>

    <section class="controls">
      <label>
        Visualização
        <select
          :value="store.viewType"
          @change="actions.setViewType($event.target.value)"
        >
          <option value="file">Arquivos</option>
          <option value="function">Funções e classes</option>
          <option value="all">Tudo</option>
        </select>
      </label>

      <label>
        Layout
        <select
          :value="store.layout"
          @change="actions.setLayout($event.target.value)"
        >
          <option value="fcose">Força (rápido)</option>
          <option value="cola">Força (viva, até 700 nós)</option>
          <option value="cose-bilkent">Força (clássico)</option>
          <option value="grid">Grade</option>
          <option value="circle">Círculo</option>
          <option value="concentric">Concêntrico</option>
          <option value="breadthfirst">Hierárquico</option>
        </select>
      </label>
    </section>

    <section v-if="store.analysisId && !store.offline" class="exports">
      <h3>Exportar</h3>
      <div class="export-buttons">
        <a
          v-for="[format, label] in EXPORTS"
          :key="format"
          class="btn"
          :href="actions.exportUrl(format)"
          download
        >
          {{ label }}
        </a>
      </div>
    </section>

    <section v-if="store.graph.nodes.length" class="nodes">
      <h3>Nós ({{ nosFiltrados.length }})</h3>
      <input v-model="filtro" type="search" placeholder="Filtrar por nome..." />

      <ul>
        <li
          v-for="node in nosFiltrados"
          :key="node.data.id"
          :class="['node-item', node.data.type, { active: store.nodeDetails?.id === node.data.id }]"
          @click="actions.selectNode(node.data.id)"
        >
          <span class="dot" :style="{ background: node.data.color }" />
          {{ node.data.label }}
        </li>
      </ul>
    </section>

    <section v-if="metricas.length" class="metrics">
      <h3>Métricas</h3>
      <dl>
        <template v-for="[label, value] in metricas" :key="label">
          <dt>{{ label }}</dt>
          <dd>{{ value }}</dd>
        </template>
      </dl>
    </section>
  </aside>
</template>

<style scoped>
.panel {
  width: 300px;
  flex-shrink: 0;
  overflow-y: auto;
  padding: 1rem;
  display: grid;
  gap: 1.5rem;
  align-content: start;
  background: var(--surface);
  border-right: 1px solid var(--border);
}

.logo {
  margin: 0;
  font-size: 1.1rem;
}

h2 {
  margin: 0 0 0.25rem;
  font-size: 0.95rem;
  word-break: break-word;
}

h3 {
  margin: 0 0 0.6rem;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.path {
  margin: 0 0 0.75rem;
  font-size: 0.7rem;
  color: var(--text-muted);
  word-break: break-all;
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.4rem;
  margin: 0 0 0.75rem;
  padding: 0;
  list-style: none;
  text-align: center;
}

.stats li {
  padding: 0.4rem 0.2rem;
  border-radius: 6px;
  background: var(--surface-alt);
}

.stats strong {
  display: block;
  font-size: 1rem;
}

.stats span {
  font-size: 0.6rem;
  color: var(--text-muted);
}

.edge-counts {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.25rem;
  font-size: 0.75rem;
}

.edge-counts li {
  display: flex;
  justify-content: space-between;
  color: var(--text-muted);
}

.edge-counts strong {
  color: var(--text);
}

.controls {
  display: grid;
  gap: 0.75rem;
}

label {
  display: grid;
  gap: 0.3rem;
  font-size: 0.75rem;
  color: var(--text-muted);
}

select,
input[type='search'] {
  width: 100%;
  padding: 0.45rem 0.5rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text);
  font-size: 0.8rem;
}

.export-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4rem;
}

.btn {
  padding: 0.4rem;
  border-radius: 6px;
  background: var(--surface-alt);
  border: 1px solid var(--border);
  color: var(--text);
  font-size: 0.75rem;
  text-align: center;
  text-decoration: none;
}

.btn:hover {
  border-color: var(--accent);
}

.nodes ul {
  margin: 0.5rem 0 0;
  padding: 0;
  list-style: none;
  max-height: 260px;
  overflow-y: auto;
  display: grid;
  gap: 0.15rem;
}

.node-item {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.35rem 0.45rem;
  border-radius: 5px;
  font-size: 0.78rem;
  cursor: pointer;
  word-break: break-word;
}

.node-item:hover {
  background: var(--surface-alt);
}

.node-item.active {
  background: color-mix(in srgb, var(--accent) 18%, transparent);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.metrics dl {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.35rem 0.5rem;
  margin: 0;
  font-size: 0.78rem;
}

.metrics dt {
  color: var(--text-muted);
}

.metrics dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
}
</style>
