<script setup>
import { onMounted, ref } from 'vue'

import GraphCanvas from '@/components/GraphCanvas.vue'
import NodeDetails from '@/components/NodeDetails.vue'
import SidePanel from '@/components/SidePanel.vue'
import { actions, store } from '@/store'

const caminho = ref('')
const usarIa = ref(false)
const semRede = ref(!navigator.onLine)

onMounted(() => {
  // Restaura a última análise: é o que torna o PWA útil sem o backend de pé
  if (actions.hydrate()) {
    caminho.value = store.project?.project_path || ''
  }

  window.addEventListener('online', () => (semRede.value = false))
  window.addEventListener('offline', () => (semRede.value = true))
})
</script>

<template>
  <div class="app">
    <SidePanel />

    <main>
      <header class="topbar">
        <form
          class="analyze"
          @submit.prevent="actions.analyze(caminho, { useAi: usarIa })"
        >
          <input
            v-model="caminho"
            type="text"
            placeholder="Caminho do projeto a analisar (Python, Dart, TS, Go, Java...)"
            :disabled="!!store.loading"
          />
          <label class="ia">
            <input v-model="usarIa" type="checkbox" :disabled="!!store.loading" />
            IA
          </label>
          <button type="submit" :disabled="!!store.loading">
            {{ store.loading ? 'Analisando...' : 'Analisar' }}
          </button>
        </form>
      </header>

      <p v-if="store.restoredFromCache" class="banner info">
        Mostrando a última análise salva neste dispositivo. Para analisar um
        projeto novo, o servidor local precisa estar rodando
        (<code>graphalyzer-api</code>).
      </p>

      <p v-if="semRede || store.offline" class="banner warn">
        Sem conexão com a API local. A análise precisa do servidor; a navegação
        pelo grafo já carregado continua funcionando.
      </p>

      <p v-if="store.error" class="banner error">
        {{ store.error }}
        <button class="dismiss" @click="actions.dismissError()">✕</button>
      </p>

      <div class="workspace">
        <GraphCanvas />
        <NodeDetails />
      </div>
    </main>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.topbar {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}

.analyze {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.analyze input[type='text'] {
  flex: 1;
  min-width: 0;
  padding: 0.5rem 0.7rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text);
  font-size: 0.85rem;
}

.ia {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.8rem;
  color: var(--text-muted);
  white-space: nowrap;
}

.analyze button {
  padding: 0.5rem 1.1rem;
  border: none;
  border-radius: 6px;
  background: var(--accent);
  color: #fff;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}

.analyze button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.workspace {
  display: flex;
  flex: 1;
  min-height: 0;
}

.banner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  padding: 0.6rem 1rem;
  font-size: 0.8rem;
  border-bottom: 1px solid var(--border);
}

.banner.info {
  background: color-mix(in srgb, var(--accent) 12%, transparent);
  color: var(--text);
}

.banner.warn {
  background: color-mix(in srgb, #f59e0b 18%, transparent);
}

.banner.error {
  background: color-mix(in srgb, #ef4444 18%, transparent);
}

.dismiss {
  margin-left: auto;
  border: none;
  background: transparent;
  cursor: pointer;
  color: inherit;
}

code {
  font-family: ui-monospace, Consolas, monospace;
}

@media (max-width: 900px) {
  .app {
    flex-direction: column;
    height: auto;
    min-height: 100vh;
  }

  .workspace {
    flex-direction: column;
    min-height: 70vh;
  }
}
</style>
