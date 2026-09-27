/**
 * Admin 列表页共享的列描述类型（key/title/class/align）。
 * 唯一消费方是 components/admin/AdminDataTable：列对象由各页面自行构造，
 * key 只作 v-for 标识、不参与取值，新增或改名字段不会有任何编译期约束，改形状要同步改表格实现。
 */
export interface AdminColumn {
  key: string
  title: string
  class?: string
  align?: 'left' | 'right' | 'center'
}
