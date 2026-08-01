<script setup>
import { computed } from 'vue'

import { actions, store } from '@/store'

const node = computed(() => store.nodeDetails)

const basics = computed(() => {
  if (!node.value) return []
  return [
    ['Tipo', node.value.type],
    ['Arquivo', node.value.file_path],
    ['Linha', node.value.line_number],
    ['Complexidade', node.value.complexity],
    ['Arestas de entrada', node.value.incoming_edges],
    ['Arestas de saída', node.value.outgoing_edges],
  ]
})

function assinatura(parameter) {
  const tipo = parameter.type ? `: ${parameter.type}` : ''
  const padrao = parameter.default ? ` = ${parameter.default}` : ''
  return `${parameter.name}${tipo}${padrao}`
}
</script>

<template>
  <aside v-if="node" class="details">
    <header>
      <h3>{{ node.name }}</h3>
      <button class="close" aria-label="Fechar" @click="actions.clearSelection()">
        ✕
      </button>
    </header>

    <div class="body">
      <section>
        <h4>Informações</h4>
        <dl>
          <template v-for="[label, value] in basics" :key="label">
            <dt>{{ label }}</dt>
            <dd>{{ value }}</dd>
          </template>
        </dl>
      </section>

      <section v-if="node.docstring">
        <h4>Documentação</h4>
        <!-- interpolação do Vue já escapa: sem v-html, sem injeção -->
        <pre class="doc">{{ node.docstring }}</pre>
      </section>

      <section v-if="node.parameters?.length">
        <h4>Parâmetros de entrada</h4>
        <ul class="params">
          <li v-for="parameter in node.parameters" :key="parameter.name">
            <code>{{ assinatura(parameter) }}</code>
          </li>
        </ul>
      </section>

      <section v-if="node.return_type">
        <h4>Retorno</h4>
        <code>{{ node.return_type }}</code>
      </section>

      <section v-if="node.decorators?.length">
        <h4>Decoradores</h4>
        <ul class="params">
          <li v-for="decorator in node.decorators" :key="decorator">
            <code>@{{ decorator }}</code>
          </li>
        </ul>
      </section>

      <section v-if="node.ai_summary">
        <h4>Análise por IA</h4>
        <p>{{ node.ai_summary }}</p>
        <p v-if="node.ai_category" class="muted">
          Categoria: {{ node.ai_category }}
        </p>
      </section>

      <section v-if="node.source_code">
        <h4>Código</h4>
        <pre class="code">{{ node.source_code }}</pre>
      </section>
    </div>
  </aside>
</template>

<style scoped>
.details {
  display: flex;
  flex-direction: column;
  width: 340px;
  border-left: 1px solid var(--border);
  background: var(--surface);
  overflow: hidden;
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--border);
}

header h3 {
  margin: 0;
  font-size: 0.95rem;
  word-break: break-word;
}

.close {
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 1rem;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
}

.close:hover {
  background: var(--surface-alt);
  color: var(--text);
}

.body {
  overflow-y: auto;
  padding: 1rem;
  display: grid;
  gap: 1.25rem;
}

h4 {
  margin: 0 0 0.5rem;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.35rem 0.75rem;
  margin: 0;
  font-size: 0.8rem;
}

dt {
  color: var(--text-muted);
}

dd {
  margin: 0;
  word-break: break-word;
}

.params {
  margin: 0;
  padding-left: 1rem;
  display: grid;
  gap: 0.3rem;
  font-size: 0.8rem;
}

code {
  font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
  font-size: 0.78rem;
}

pre {
  margin: 0;
  padding: 0.65rem;
  border-radius: 6px;
  background: var(--surface-alt);
  font-size: 0.75rem;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 260px;
  overflow: auto;
}

.doc {
  font-family: inherit;
}

.muted {
  color: var(--text-muted);
  font-size: 0.8rem;
  margin: 0.35rem 0 0;
}
</style>
