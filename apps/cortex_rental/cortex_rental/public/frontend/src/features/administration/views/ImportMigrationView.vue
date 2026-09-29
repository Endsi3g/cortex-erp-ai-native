<template>
  <div class="cx-page" data-test="screen-import">
    <CortexPageHeader title="Import et migration" subtitle="Apportez vos données avec « Data Import » : aperçu, validation ligne par ligne et journal d'erreurs avant toute écriture." :provenance="data?.provenance">
      <template #actions><RefreshButton :loading="loading" @refresh="reload" /></template>
    </CortexPageHeader>

    <div v-if="error" class="cx-section"><CortexErrorBanner :error-message="error" @retry="reload" /></div>
    <div v-else-if="loading && !data" class="cx-section"><CortexSkeleton variant="table-row" :count="4" /></div>

    <template v-else-if="data">
      <section class="cx-section" aria-labelledby="steps-title">
        <h2 id="steps-title">Comment importer</h2>
        <ol class="cx-list" style="list-style: decimal inside">
          <li><span><strong>Choisissez ce que vous importez</strong> ci-dessous ; le modèle de fichier est téléchargeable à l'étape suivante.</span></li>
          <li><span><strong>Remplissez le modèle</strong> (CSV ou Excel) à partir de votre ancien système.</span></li>
          <li><span><strong>Lancez l'aperçu</strong> : rien n'est créé tant que vous n'avez pas confirmé, et chaque erreur est indiquée avec sa ligne.</span></li>
          <li><span><strong>Vérifiez le résultat</strong> dans l'historique ci-dessous, puis dans le catalogue.</span></li>
        </ol>
      </section>

      <section class="cx-section" aria-labelledby="targets-title">
        <h2 id="targets-title">Que voulez-vous importer ?</h2>
        <div v-if="!data.targets.length" class="cx-notice" role="status"><div>Votre rôle ne permet pas de lancer un import. Demandez à un administrateur de le faire ou de vous en donner le droit.</div></div>
        <div v-else class="cx-onb__choices">
          <a v-for="target in data.targets" :key="target.doctype" class="cx-btn-secondary" :href="target.url" :title="target.description">{{ target.label }}</a>
        </div>
        <dl v-if="data.targets.length" class="cx-dl" style="padding-top: 12px"><div v-for="target in data.targets" :key="target.doctype"><dt>{{ target.label }}</dt><dd>{{ target.description }}</dd></div></dl>
      </section>

      <section class="cx-section" aria-labelledby="history-title">
        <h2 id="history-title">Imports récents de votre équipe</h2>
        <div v-if="!data.history.length" class="cx-empty"><strong>Aucun import</strong>Les imports lancés par votre équipe apparaîtront ici.</div>
        <div v-else class="cx-tablewrap">
          <table class="cx-table">
            <thead><tr><th scope="col">Import</th><th scope="col">Type de données</th><th scope="col">Mode</th><th scope="col">État</th><th scope="col">Lancé par</th><th scope="col">Date</th></tr></thead>
            <tbody>
              <tr v-for="row in data.history" :key="row.name">
                <td><a :href="row.url">{{ row.name }}</a></td>
                <td>{{ row.doctype }}</td>
                <td>{{ row.import_type === 'Update Existing Records' ? 'Mise à jour' : 'Création' }}</td>
                <td><span class="cx-tag" :class="statusClass(row.status)">{{ statusLabel(row.status) }}</span></td>
                <td>{{ row.by }}</td>
                <td>{{ formatDate(row.created) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { formatDate } from '@/app/i18n/formatters'
import { getCortexApiClient } from '@/api'
import CortexErrorBanner from '@/design-system/components/states/CortexErrorBanner.vue'
import CortexSkeleton from '@/design-system/components/states/CortexSkeleton.vue'
import CortexPageHeader from '@/features/common/components/CortexPageHeader.vue'
import RefreshButton from '@/features/common/components/RefreshButton.vue'
import { useResource } from '@/features/common/composables/useResource'

const { data, loading, error, reload } = useResource(() => getCortexApiClient().getImports())

const labels: Record<string, string> = { Pending: 'En attente', Success: 'Réussi', 'Partial Success': 'Réussi en partie', Error: 'Erreur', 'In Progress': 'En cours' }
const statusLabel = (status?: string | null) => (status ? labels[status] ?? status : '—')
const statusClass = (status?: string | null) => (status === 'Success' ? 'cx-tag--ok' : status === 'Error' ? 'cx-tag--bad' : status === 'Partial Success' ? 'cx-tag--warn' : '')
</script>
