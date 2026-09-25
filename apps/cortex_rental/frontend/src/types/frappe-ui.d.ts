import type { DefineComponent } from 'vue'

declare module 'frappe-ui' {
  export const FrappeUIProvider: DefineComponent<{}, {}, any>
  export const Button: DefineComponent<any, any, any>
  export const TextInput: DefineComponent<any, any, any>
  export const Input: DefineComponent<any, any, any>
  export const Textarea: DefineComponent<any, any, any>
  export const Select: DefineComponent<any, any, any>
  export const Badge: DefineComponent<any, any, any>
  export const Avatar: DefineComponent<any, any, any>
  export const Card: DefineComponent<any, any, any>
  export const Dialog: DefineComponent<any, any, any>
  export const Dropdown: DefineComponent<any, any, any>
  export const Tooltip: DefineComponent<any, any, any>
  export const Toast: DefineComponent<any, any, any>
  export const toast: any
  export const Tree: DefineComponent<any, any, any>
  export const Sidebar: DefineComponent<any, any, any>
  export const SidebarItem: DefineComponent<any, any, any>
  export const SidebarHeader: DefineComponent<any, any, any>
  export const SidebarSection: DefineComponent<any, any, any>
  export const FeatherIcon: DefineComponent<any, any, any>
  export const LoadingIndicator: DefineComponent<any, any, any>
  export const Spinner: DefineComponent<any, any, any>
  export const Divider: DefineComponent<any, any, any>
  export const Switch: DefineComponent<any, any, any>
  export const Popover: DefineComponent<any, any, any>
  export const Tabs: DefineComponent<any, any, any>
  export const TabButtons: DefineComponent<any, any, any>
  export const Breadcrumbs: DefineComponent<any, any, any>
  export const Checkbox: DefineComponent<any, any, any>
  export const DatePicker: DefineComponent<any, any, any>
  export const ListView: DefineComponent<any, any, any>
  export const ECharts: DefineComponent<any, any, any>
  export const AxisChart: DefineComponent<any, any, any>
  export const NumberChart: DefineComponent<any, any, any>
  export const DonutChart: DefineComponent<any, any, any>
  export const CommandPalette: DefineComponent<any, any, any>
  export const KeyboardShortcut: DefineComponent<any, any, any>
  export const ConfirmDialog: DefineComponent<any, any, any>
  export const Autocomplete: DefineComponent<any, any, any>
  export const Combobox: DefineComponent<any, any, any>
  export const MultiSelect: DefineComponent<any, any, any>
  export const FormControl: DefineComponent<any, any, any>
  export const ErrorMessage: DefineComponent<any, any, any>
  export const Progress: DefineComponent<any, any, any>
  export const Calendar: DefineComponent<any, any, any>
  export const FileUploader: DefineComponent<any, any, any>
  export const Alert: DefineComponent<any, any, any>
  export const ListFilter: DefineComponent<any, any, any>
  export const Rating: DefineComponent<any, any, any>
  export const TimePicker: DefineComponent<any, any, any>
  export const call: (method: string, args?: Record<string, unknown>) => Promise<any>
}

declare module 'frappe-ui/vite' {
  const plugin: (options?: any) => any
  export default plugin
}

declare module 'frappe-ui/tailwind' {
  const preset: any
  export const content: string[]
  export default preset
}
