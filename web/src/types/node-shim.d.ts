declare module 'node:fs' {
  export * from 'fs'
  import fsDefault from 'fs'
  export default fsDefault
}

declare module 'node:path' {
  export * from 'path'
  import pathDefault from 'path'
  export default pathDefault
}
