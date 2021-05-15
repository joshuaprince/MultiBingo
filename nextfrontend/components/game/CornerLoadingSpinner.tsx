import { Spinner } from "@chakra-ui/react"
import React from "react"

import styles from "styles/Game.module.scss"

export const CornerLoadingSpinner: React.FunctionComponent = () => {
  return (
    <div className={styles.cornerLoading}>
      Connecting...
      <Spinner/>
    </div>
  )
}
