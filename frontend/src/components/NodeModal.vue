<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { actions, store } from '@/store'

const no = computed(() => store.nodeDetails)
const codigoAberto = ref(false)
const fechar = ref(null)

const TIPOS = { function: 'Função', class: 'Classe', file: 'Arquivo', module: 'Módulo' }

const local = computed(() => {
  if (!no.value) return ''
  const linha = no.value.line_number ? `:${no.value.line_number}` : ''
  return `${no.value.file_path}${linha}`
})

// Parâmetros declarados e o que de fato chega pelas arestas são coisas
// diferentes: os dois entram, separados, para não parecerem a mesma lista.
const entradasDeFluxo = computed(() => {
  const vistos = new Set()
  return (no.value?.entradas || []).filter((e) => {
    const chave = `${e.variavel}|${e.origem}`
    if (vistos.has(chave)) return false
    vistos.add(chave)
    return true
  })
})

const saidasDeFluxo = computed(() => {
  const vistos = new Set()
  return (no.value?.saidas || []).filter((s) => {
    const chave = `${s.variavel}|${s.destino}`
    if (vistos.has(chave)) return false
    vistos.add(chave)
    return true
  })
})

// Contagem por tipo em vez de um total solto: um nó com 3 arestas de import
// mostrava "Entradas 3" e a seção vazia logo abaixo.
const RELACAO = { fluxo: 'fluxo', chamadas: 'chamadas', imports: 'imports', contencao: 'contenção' }

function detalhar(resumo) {
  // Detalhe vindo de um cache antigo não tem o resumo: melhor omitir a
  // métrica do que mostrar um rótulo sem valor ao lado.
  if (!resumo) return ''
  const partes = Object.entries(resumo)
    .filter(([, n]) => n > 0)
    .map(([k, n]) => `${n} ${RELACAO[k] || k}`)
  return partes.join(' · ') || 'nenhuma'
}

const entram = computed(() => detalhar(no.value?.resumo_das_relacoes?.entram))
const saem = computed(() => detalhar(no.value?.resumo_das_relacoes?.saem))

// Grupos que só aparecem quando têm conteúdo
const grupos = computed(() => {
  const n = no.value
  if (!n) return []
  return [
    ['Contido em', n.contido_em],
    ['Contém', n.contem],
    ['Chamada por', n.chamado_por],
    ['Chama', n.chama],
    ['Importado por', n.importado_por],
    ['Importa', n.importa],
  ].filter(([, itens]) => itens?.length)
})

function aoTeclar(evento) {
  if (evento.key === 'Escape' && no.value) actions.clearSelection()
}

onMounted(() => window.addEventListener('keydown', aoTeclar))
onBeforeUnmount(() => window.removeEventListener('keydown', aoTeclar))

// Reabrir para outro nó volta o código ao estado recolhido e devolve o foco
watch(
  () => no.value?.id,
  async (id) => {
    codigoAberto.value = false
    if (id) {
      await Promise.resolve()
      fechar.value?.focus()
    }
  },
)
</script>

<template>
  <Teleport to="body">
    <div
      v-if="no"
      class="fundo"
      role="dialog"
      aria-modal="true"
      :aria-label="`Detalhes de ${no.name}`"
      @click.self="actions.clearSelection()"
    >
      <div class="janela">
        <header>
          <div class="identificacao">
            <span class="tipo">{{ TIPOS[no.type] || no.type }}</span>
            <h2>{{ no.name }}</h2>
          </div>
          <button ref="fechar" class="fechar" aria-label="Fechar" @click="actions.clearSelection()">
            ✕
          </button>
        </header>

        <p class="local">{{ local }}</p>

        <div class="corpo">
          <section v-if="no.signature" class="assinatura">
            <code>{{ no.signature }}</code>
          </section>

          <p v-if="no.docstring" class="doc">{{ no.docstring }}</p>
          <p v-else-if="no.ai_summary" class="doc">{{ no.ai_summary }}</p>

          <div class="colunas">
            <section>
              <h3>📥 Entradas</h3>

              <template v-if="no.parameters?.length">
                <p class="rotulo">Parâmetros</p>
                <ul class="itens">
                  <li v-for="p in no.parameters" :key="p.name">
                    <code>{{ p.name }}</code>
                    <span v-if="p.type" class="tipo-dado">{{ p.type }}</span>
                    <span v-if="p.default" class="padrao">= {{ p.default }}</span>
                  </li>
                </ul>
              </template>

              <template v-if="entradasDeFluxo.length">
                <p class="rotulo">Recebe de</p>
                <ul class="itens">
                  <li v-for="e in entradasDeFluxo" :key="`${e.variavel}${e.origem}`">
                    <code>{{ e.variavel }}</code>
                    <span v-if="e.tipo" class="tipo-dado">{{ e.tipo }}</span>
                    <button class="salto" @click="actions.selectNode(e.origem_id)">
                      ← {{ e.origem }}
                    </button>
                  </li>
                </ul>
              </template>

              <p v-if="!no.parameters?.length && !entradasDeFluxo.length" class="vazio">
                Nenhum parâmetro nem fluxo de dados de entrada.
                <template v-if="entram && entram !== 'nenhuma'">
                  As relações que chegam ({{ entram }}) estão abaixo.
                </template>
              </p>
            </section>

            <section>
              <h3>📤 Saídas</h3>

              <template v-if="no.return_type">
                <p class="rotulo">Retorno</p>
                <ul class="itens">
                  <li><code>{{ no.return_type }}</code></li>
                </ul>
              </template>

              <template v-if="saidasDeFluxo.length">
                <p class="rotulo">Envia para</p>
                <ul class="itens">
                  <li v-for="s in saidasDeFluxo" :key="`${s.variavel}${s.destino}`">
                    <code>{{ s.variavel }}</code>
                    <span v-if="s.tipo" class="tipo-dado">{{ s.tipo }}</span>
                    <button class="salto" @click="actions.selectNode(s.destino_id)">
                      → {{ s.destino }}
                    </button>
                  </li>
                </ul>
              </template>

              <p v-if="!no.return_type && !saidasDeFluxo.length" class="vazio">
                Nenhum retorno nem fluxo de dados de saída.
                <template v-if="saem && saem !== 'nenhuma'">
                  As relações que saem ({{ saem }}) estão abaixo.
                </template>
              </p>
            </section>
          </div>

          <section v-if="grupos.length" class="relacoes">
            <h3>🔗 Relações</h3>
            <div class="grupos">
              <div v-for="[titulo, itens] in grupos" :key="titulo">
                <p class="rotulo">{{ titulo }} ({{ itens.length }})</p>
                <div class="fichas">
                  <button
                    v-for="item in itens"
                    :key="item.id"
                    class="ficha"
                    :title="item.rotulo || item.tipo"
                    @click="actions.selectNode(item.id)"
                  >
                    {{ item.nome }}
                  </button>
                </div>
              </div>
            </div>
          </section>

          <section class="metricas">
            <span>Complexidade <strong>{{ no.complexity }}</strong></span>
            <span v-if="entram">Entram <strong>{{ entram }}</strong></span>
            <span v-if="saem">Saem <strong>{{ saem }}</strong></span>
            <span v-if="no.ai_category">Categoria <strong>{{ no.ai_category }}</strong></span>
          </section>

          <section v-if="no.source_code">
            <button class="alternar" @click="codigoAberto = !codigoAberto">
              {{ codigoAberto ? '▾' : '▸' }} Código
            </button>
            <!-- interpolação do Vue escapa: sem v-html, sem injeção -->
            <pre v-if="codigoAberto" class="codigo">{{ no.source_code }}</pre>
          </section>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.fundo {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  background: rgba(10, 11, 18, 0.72);
  backdrop-filter: blur(2px);
}

.janela {
  width: min(760px, 100%);
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.45);
  overflow: hidden;
}

header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.1rem 0.4rem;
}

.identificacao {
  min-width: 0;
}

.tipo {
  font-size: 0.63rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}

h2 {
  margin: 0.15rem 0 0;
  font-size: 1.15rem;
  word-break: break-word;
}

.fechar {
  flex-shrink: 0;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 1rem;
  cursor: pointer;
  padding: 0.3rem 0.5rem;
  border-radius: 6px;
}

.fechar:hover {
  background: var(--surface-alt);
  color: var(--text);
}

.local {
  margin: 0;
  padding: 0 1.1rem 0.75rem;
  font-size: 0.7rem;
  color: var(--text-muted);
  word-break: break-all;
  border-bottom: 1px solid var(--border);
}

.corpo {
  overflow-y: auto;
  padding: 1rem 1.1rem 1.2rem;
  display: grid;
  gap: 1.1rem;
}

.assinatura code {
  display: block;
  padding: 0.65rem 0.75rem;
  border-radius: 8px;
  background: var(--surface-alt);
  font-size: 0.82rem;
  word-break: break-word;
}

.doc {
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.5;
  color: var(--text);
  white-space: pre-wrap;
}

.colunas {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.1rem;
}

h3 {
  margin: 0 0 0.5rem;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.rotulo {
  margin: 0.55rem 0 0.25rem;
  font-size: 0.65rem;
  color: var(--text-muted);
}

.itens {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.3rem;
}

.itens li {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
  font-size: 0.78rem;
}

code {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 0.78rem;
}

.tipo-dado {
  padding: 0.05rem 0.35rem;
  border-radius: 4px;
  background: color-mix(in srgb, var(--accent) 16%, transparent);
  color: var(--accent);
  font-size: 0.68rem;
}

.padrao {
  color: var(--text-muted);
  font-size: 0.7rem;
}

.salto,
.ficha {
  border: 1px solid var(--border);
  background: var(--surface-alt);
  color: var(--text);
  font-size: 0.7rem;
  padding: 0.1rem 0.4rem;
  border-radius: 5px;
  cursor: pointer;
}

.salto:hover,
.ficha:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.fichas {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}

.relacoes .grupos {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 0.7rem;
}

.vazio {
  margin: 0;
  font-size: 0.76rem;
  color: var(--text-muted);
}

.metricas {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  padding-top: 0.8rem;
  border-top: 1px solid var(--border);
  font-size: 0.73rem;
  color: var(--text-muted);
}

.metricas strong {
  color: var(--text);
  font-variant-numeric: tabular-nums;
}

.alternar {
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  cursor: pointer;
  padding: 0;
}

.alternar:hover {
  color: var(--text);
}

.codigo {
  margin: 0.5rem 0 0;
  padding: 0.7rem;
  border-radius: 8px;
  background: var(--surface-alt);
  font-size: 0.74rem;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 320px;
  overflow: auto;
}

@media (max-width: 680px) {
  .colunas {
    grid-template-columns: 1fr;
  }
}
</style>
