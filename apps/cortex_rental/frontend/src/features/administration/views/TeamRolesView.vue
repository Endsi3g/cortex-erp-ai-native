<template>
  <div class="flex min-h-full flex-col bg-surface-white">
    <PageHeader :title="t('routes.team_roles')">
      <template #title-suffix>
        <Tooltip v-if="team?.provenance === 'mock'" :text="t('admin.demo_notice')">
          <Badge theme="orange" variant="subtle" size="md" role="status">DEMO</Badge>
        </Tooltip>
      </template>
      <template #actions>
        <Button size="sm" variant="subtle" @click="openErpnextUsers">
          <template #prefix><ExternalLink class="size-4" :stroke-width="1.5" /></template>
          {{ t('admin.team.manage_users') }}
        </Button>
      </template>
    </PageHeader>

    <PageFilters :label="t('routes.team_roles')">
      <TextInput v-model="search" type="search" size="sm" variant="subtle" class="lg:col-span-2" :placeholder="t('admin.team.search')" :aria-label="t('admin.team.search')" />
      <FormControl v-model="roleFilter" type="select" size="sm" variant="subtle" :aria-label="t('admin.team.role')" :options="roleOptions" />
    </PageFilters>
    <p v-if="errorMessage" class="mx-6 mt-4 rounded border border-outline-red-1 bg-surface-red-1 px-4 py-2 text-p-sm text-ink-red-4" role="alert">{{ errorMessage }}</p>

    <div class="mt-6">
      <DataTable
        :label="t('admin.team.people')"
        :columns="columns"
        :rows="visibleUsers"
        row-key="user"
        :loading="loading"
        :empty-text="t('admin.team.empty')"
        clickable
        @row-click="row => openMember(row as TeamMember)"
      >
        <template #cell-full_name="{ row }">
          <span class="text-ink-gray-9">{{ row.full_name }}</span>
          <span v-if="row.is_self" class="ml-2 text-ink-gray-5">{{ t('admin.team.you') }}</span>
          <Badge v-if="!row.enabled" class="ml-2" theme="gray" variant="subtle">{{ t('admin.inactive') }}</Badge>
        </template>
        <template #cell-roles="{ row }">
          <div class="flex flex-wrap gap-1 py-1">
            <Badge v-for="role in cortexRoles(row as TeamMember)" :key="role" theme="blue" variant="subtle">{{ roleLabel(role) }}</Badge>
            <span v-if="otherRoles(row as TeamMember).length" class="text-ink-gray-5">{{ t('admin.team.other_roles', { count: otherRoles(row as TeamMember).length }) }}</span>
          </div>
        </template>
      </DataTable>
    </div>

    <section v-if="team?.service_accounts.length" class="mt-8 pb-6" :aria-labelledby="`${uid}-services`">
      <h2 :id="`${uid}-services`" class="px-6 text-base font-semibold text-ink-gray-9">{{ t('admin.team.service_accounts') }}</h2>
      <p class="px-6 pb-3 pt-1 text-p-sm text-ink-gray-5">{{ t('admin.team.service_hint') }}</p>
      <DataTable :label="t('admin.team.service_accounts')" :columns="serviceColumns" :rows="team.service_accounts" row-key="user" :filter-row="false" />
    </section>

    <Dialog v-model="memberOpen" :options="{ title: member?.full_name ?? '', size: 'lg' }">
      <template #body-content>
        <div v-if="member" class="space-y-4">
          <p class="text-p-sm text-ink-gray-5">{{ member.user }}</p>
          <p v-if="member.is_self" class="rounded border border-outline-amber-2 bg-surface-amber-1 px-3 py-2 text-p-sm text-ink-gray-8">{{ t('admin.team.self_locked') }}</p>
          <fieldset class="space-y-2" :disabled="member.is_self">
            <legend class="mb-2 text-sm font-medium text-ink-gray-7">{{ t('admin.team.cortex_roles') }}</legend>
            <label v-for="role in team?.manageable_roles ?? []" :key="role" class="flex items-start gap-2 text-base">
              <Checkbox class="mt-0.5" :model-value="draftRoles.has(role)" :disabled="member.is_self" @update:model-value="(value: boolean) => toggleRole(role, value)" />
              <span>
                <span class="text-ink-gray-9">{{ roleLabel(role) }}</span>
                <span class="block text-p-sm text-ink-gray-5">{{ roleDescription(role) }}</span>
              </span>
            </label>
          </fieldset>
          <div v-if="otherRoles(member).length">
            <p class="text-sm font-medium text-ink-gray-7">{{ t('admin.team.untouched_roles') }}</p>
            <p class="mt-1 text-p-sm text-ink-gray-5">{{ otherRoles(member).join(', ') }}</p>
          </div>
          <p v-if="changeSummary" class="text-p-sm text-ink-gray-7">{{ changeSummary }}</p>
          <p v-if="saveError" class="text-p-sm text-ink-red-4" role="alert">{{ saveError }}</p>
        </div>
      </template>
      <template #actions="{ close }">
        <div class="flex items-center justify-between gap-2">
          <span class="text-p-sm text-ink-gray-5">{{ t('admin.audited_hint') }}</span>
          <div class="flex gap-2">
            <Button variant="subtle" :disabled="saving" @click="close">{{ t('common.cancel') }}</Button>
            <Button variant="solid" :loading="saving" :disabled="!member || member.is_self || !changeSummary" @click="saveRoles">{{ t('admin.save') }}</Button>
          </div>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import { Badge, Button, Checkbox, Dialog, FormControl, TextInput, Tooltip, toast } from 'frappe-ui'
import { ExternalLink } from 'lucide-vue-next'
import PageHeader from '@/design-system/components/page/PageHeader.vue'
import PageFilters from '@/design-system/components/page/PageFilters.vue'
import DataTable, { type DataTableColumn } from '@/design-system/components/page/DataTable.vue'
import { getCortexApiClient } from '@/api'
import type { Team, TeamMember } from '@/api/contracts/administration'
import { formatDateTime } from '@/app/i18n/formatters'
import type { LocaleType } from '@/app/i18n'

const { t, te, locale } = useI18n()
const uid = useId()

const team = ref<Team | null>(null)
const loading = ref(false)
const errorMessage = ref('')
const search = ref('')
const roleFilter = ref('')
const member = ref<TeamMember | null>(null)
const memberOpen = ref(false)
const draftRoles = ref(new Set<string>())
const saving = ref(false)
const saveError = ref('')

const slug = (role: string) => role.toLowerCase().replace(/[^a-z0-9]+/g, '_')
const roleLabel = (role: string) => (te(`admin.roles.${slug(role)}.label`) ? t(`admin.roles.${slug(role)}.label`) : role)
const roleDescription = (role: string) => (te(`admin.roles.${slug(role)}.description`) ? t(`admin.roles.${slug(role)}.description`) : '')
const manageable = computed(() => new Set(team.value?.manageable_roles ?? []))
const cortexRoles = (row: TeamMember) => row.roles.filter(role => manageable.value.has(role))
const otherRoles = (row: TeamMember) => row.roles.filter(role => !manageable.value.has(role) && !['All', 'Guest', 'Desk User'].includes(role))

const roleOptions = computed(() => [{ label: t('admin.team.all_roles'), value: '' }, ...(team.value?.manageable_roles ?? []).map(value => ({ label: roleLabel(value), value }))])

const columns = computed<DataTableColumn<TeamMember>[]>(() => [
  { key: 'full_name', label: t('admin.team.name'), width: '260px' },
  { key: 'user', label: t('admin.team.email'), width: '260px' },
  { key: 'roles', label: t('admin.team.cortex_roles'), width: '420px', sortable: false },
  { key: 'last_login', label: t('admin.team.last_login'), width: '180px', format: row => (row.last_login ? formatDateTime(row.last_login, locale.value as LocaleType) : '—') }
])
const serviceColumns = computed<DataTableColumn<TeamMember>[]>(() => [
  { key: 'user', label: t('admin.team.account'), width: '260px' },
  { key: 'roles', label: t('admin.team.roles'), width: '420px', format: row => row.roles.join(', ') },
  { key: 'last_login', label: t('admin.team.last_login'), width: '180px', format: row => (row.last_login ? formatDateTime(row.last_login, locale.value as LocaleType) : '—') }
])

const visibleUsers = computed(() => {
  const needle = search.value.trim().toLowerCase()
  return (team.value?.users ?? []).filter(user =>
    (!needle || user.full_name.toLowerCase().includes(needle) || user.user.toLowerCase().includes(needle)) &&
    (!roleFilter.value || user.roles.includes(roleFilter.value))
  )
})

const changeSummary = computed(() => {
  if (!member.value) return ''
  const before = new Set(cortexRoles(member.value))
  const add = [...draftRoles.value].filter(role => !before.has(role)).map(roleLabel)
  const remove = [...before].filter(role => !draftRoles.value.has(role)).map(roleLabel)
  const parts = []
  if (add.length) parts.push(t('admin.team.will_add', { roles: add.join(', ') }))
  if (remove.length) parts.push(t('admin.team.will_remove', { roles: remove.join(', ') }))
  return parts.join(' ')
})

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    team.value = await getCortexApiClient().listTeam()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

function openMember(row: TeamMember) {
  member.value = row
  draftRoles.value = new Set(cortexRoles(row))
  saveError.value = ''
  memberOpen.value = true
}

function toggleRole(role: string, value: boolean) {
  const next = new Set(draftRoles.value)
  if (value) next.add(role)
  else next.delete(role)
  draftRoles.value = next
}

async function saveRoles() {
  if (!member.value) return
  saving.value = true
  saveError.value = ''
  try {
    team.value = await getCortexApiClient().setUserRoles(member.value.user, [...draftRoles.value])
    memberOpen.value = false
    toast.create({ message: t('admin.saved'), type: 'success' })
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : String(error)
  } finally {
    saving.value = false
  }
}

function openErpnextUsers() {
  window.open('/app/user', '_blank', 'noopener')
}

onMounted(load)
</script>
