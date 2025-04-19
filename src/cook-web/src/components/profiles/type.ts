type ProfileType = 'system' | 'custom'
type DataType = 'string' | 'enum'

interface EnumItem {
  value: string
  title: string
}

interface Profile {
  id?: string
  name: string
  title: string
  type: ProfileType
  dataType: DataType
  defaultValue?: string
  enumItems?: EnumItem[]
}

export type { ProfileType, DataType, EnumItem, Profile }