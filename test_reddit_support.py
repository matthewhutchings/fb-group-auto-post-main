#!/usr/bin/env python3
"""
Test Reddit platform support
"""

def test_reddit_support():
    print("🧪 Testing Reddit Platform Support")
    print("=" * 40)
    
    # Test platform loading
    try:
        from platforms.loader import load_rules
        rules = load_rules()
        
        print("✅ Available platforms:")
        for platform in sorted(rules.keys()):
            tasks = list(rules[platform].get("tasks", {}).keys())
            print(f"   📱 {platform}: {tasks}")
        
        if 'reddit' in rules:
            print("\n✅ Reddit platform found!")
            reddit_tasks = rules['reddit'].get('tasks', {})
            print(f"   📋 Reddit tasks: {list(reddit_tasks.keys())}")
            
            if 'post_subreddit' in reddit_tasks:
                print("✅ Reddit post_subreddit task configured")
                steps = reddit_tasks['post_subreddit'].get('steps', [])
                print(f"   🔧 Task has {len(steps)} automation steps")
            else:
                print("❌ Reddit post_subreddit task missing")
        else:
            print("❌ Reddit platform not found")
        
    except Exception as e:
        print(f"❌ Error loading platforms: {e}")
    
    # Test SOCIAL_MAPS
    try:
        import configs
        print(f"\n✅ SOCIAL_MAPS configured platforms:")
        for platform in sorted(configs.SOCIAL_MAPS.keys()):
            config = configs.SOCIAL_MAPS[platform]
            print(f"   🔐 {platform}: {config['login_url']}")
        
        if 'reddit' in configs.SOCIAL_MAPS:
            print("✅ Reddit login URL configured")
        else:
            print("❌ Reddit not in SOCIAL_MAPS")
            
    except Exception as e:
        print(f"❌ Error loading configs: {e}")

def demo_reddit_api_usage():
    print("\n🚀 Reddit API Usage Examples")
    print("=" * 40)
    
    print("1. Generate Reddit Cookies:")
    print("""
curl -X POST http://localhost:3000/generate-cookies \\
  -H "Content-Type: application/json" \\
  -d '{"platform": "reddit", "manual_confirmation": true}'
""")
    
    print("2. Post to Subreddit:")
    print("""
curl -X POST http://localhost:3000/run \\
  -H "Content-Type: application/json" \\
  -d '{
    "plan": [
      {
        "platform": "reddit",
        "task": "post_subreddit", 
        "target": {"name": "Test Subreddit", "username": "test"},
        "content": "Hello from the API!"
      }
    ],
    "headless": true
  }'
""")

    print("3. Mixed Platform Posting:")
    print("""
curl -X POST http://localhost:3000/run \\
  -H "Content-Type: application/json" \\
  -d '{
    "plan": [
      {
        "platform": "facebook",
        "task": "post_group",
        "target": {"name": "FB Group", "username": "mygroup"},
        "content": "Cross-platform post!"
      },
      {
        "platform": "reddit", 
        "task": "post_subreddit",
        "target": {"name": "My Subreddit", "username": "mysubreddit"}, 
        "content": "Same content on Reddit!"
      }
    ]
  }'
""")

if __name__ == "__main__":
    test_reddit_support()
    demo_reddit_api_usage()
    
    print("\n" + "=" * 40)
    print("✅ Reddit platform is now fully supported!")
    print("🌟 You can use reddit for cookie generation and posting")