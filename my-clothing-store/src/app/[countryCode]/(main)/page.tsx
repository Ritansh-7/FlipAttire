import { Metadata } from "next"

import HMStorefront from "@modules/hm-storefront"

export const metadata: Metadata = {
  title: "FlipAttire · Your personal edit",
  description: "Personalised fashion recommendations powered by FlipAttire and Medusa.",
}

export default async function Home(props: {
  params: Promise<{ countryCode: string }>
}) {
  return <HMStorefront />
}
