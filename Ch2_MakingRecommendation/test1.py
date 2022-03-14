from recommendations import critics
import recommendations

print(critics['Lisa Rose']['Lady in the Water'])

critics['Toby']['Snakes on a Plane'] = 4.5
print(critics['Toby'])


print('print sim_distance function')
print(recommendations.sim_distance(recommendations.critics, \
                                   'Lisa Rose', 'Gene Seymour'))


print('print sim_pearson function')
print(recommendations.sim_pearson(recommendations.critics, \
                                   'Lisa Rose', 'Gene Seymour'))

print('print topMatches function')
print(recommendations.topMatches(recommendations.critics, 'Toby', n = 3))



print('print getRecommendations function')
recommendations.getRecommendations
print(recommendations.getRecommendations(recommendations.critics, 'Toby'))
print(recommendations.getRecommendations(recommendations.critics, 'Toby', similarity = recommendations.sim_distance))


movies = recommendations.transformPrefs(critics)
print(recommendations.topMatches(movies, 'Superman Returns'))
print(recommendations.getRecommendations(movies, 'Just My Luck'))


print('\n'*2+'#'*15)
itemsim = recommendations.calculateSimilarItems(critics)
print(itemsim)


print('\n'*2+'#'*15)
print(recommendations.getRecommendedItems(critics, itemsim, 'Toby'))

print('\n'*2+'#'*15)
prefs = recommendations.loadMovieLens()
print(prefs['87'])



print('\n'*2+'#'*15)
itemsim = recommendations.calculateSimilarItems(prefs, n = 50)
print(recommendations.getRecommendedItems(prefs, itemsim, '87')[:30])
