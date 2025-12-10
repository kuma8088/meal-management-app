import { useRouter } from 'next/router'
import { useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { Loading } from '@/components'

export default function Home() {
  const router = useRouter()
  const { data: session, status } = useSession()

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login')
    } else if (status === 'authenticated') {
      router.push('/home')
    }
  }, [status, router])

  return <Loading fullScreen message="リダイレクト中..." />
}

// Static page を無効化（useSession を使用するため）
export const getServerSideProps = async () => {
  return {
    props: {},
  }
}
