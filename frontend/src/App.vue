<template>
  <RouterView v-slot="{ Component, route }">
    <Transition name="route-flow" mode="out-in">
      <component :is="Component" :key="route.meta.guestOnly ? route.fullPath : 'platform-shell'" />
    </Transition>
  </RouterView>
</template>
